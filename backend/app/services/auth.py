"""
Authentication service (EOS-01 a): sign-in with lockout, session validation, sign-out and
password change.

Every operation ends with exactly one commit, so the failure counter, the lock and the audit
event of a failed sign-in are stored together. Every failed sign-in gives the same message,
whether the e-mail is unknown, the password wrong or the account locked, so the answer does not
reveal which accounts exist. The clock is injected so that tests can move time.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.security import (
    PASSWORD_MAX_LENGTH,
    generate_session_token,
    hash_password,
    hash_session_token,
    password_needs_rehash,
    validate_password_policy,
    verify_dummy_password,
    verify_password,
)
from app.models.identity import (
    AuthEvent,
    AuthEventType,
    Organization,
    OrganizationMembership,
    User,
    UserSession,
)
from app.repositories.identity import IdentityRepository, normalize_email

# last_seen_at is written at most this often, so an active page does not write on every request.
LAST_SEEN_WRITE_INTERVAL = timedelta(seconds=60)


class AuthError(Exception):
    """Base class; the message is safe to show to the user."""


class InvalidCredentialsError(AuthError):
    """Sign-in failed: one message for every reason."""


class SessionInvalidError(AuthError):
    """The session token is missing, unknown, revoked or expired."""


class PasswordChangeError(AuthError):
    """The password change was refused."""


@dataclass(frozen=True)
class RequestContext:
    """Where a request came from, for the audit trail."""

    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class AuthenticatedSession:
    """The signed-in user with the organization and role of this session."""

    user: User
    organization: Organization
    membership: OrganizationMembership
    session: UserSession

    @property
    def role(self) -> str:
        return self.membership.role


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are stored as UTC."""

    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    """Sign-in, session validation, sign-out and password change."""

    def __init__(
        self,
        repository: IdentityRepository,
        *,
        settings: Settings | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or default_settings
        self._now = now or (lambda: datetime.now(UTC))

    @property
    def sign_in_failed_message(self) -> str:
        return (
            "Sign-in failed. Check the e-mail and the password; after "
            f"{self.settings.LOGIN_MAX_FAILED_ATTEMPTS} failed attempts an account is locked "
            f"for {self.settings.LOGIN_LOCKOUT_MINUTES} minutes."
        )

    # -- sign-in --------------------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        context: RequestContext | None = None,
    ) -> tuple[str, AuthenticatedSession]:
        """Return the new session token and the signed-in identity, or raise."""

        context = context or RequestContext()
        now = self._now()
        email_normalized = normalize_email(email)
        user = await self.repository.get_user_by_email(email_normalized)

        if user is None or len(password) > PASSWORD_MAX_LENGTH:
            verify_dummy_password(password[:PASSWORD_MAX_LENGTH])
            detail = "unknown e-mail" if user is None else "password too long"
            await self._fail(AuthEventType.LOGIN_FAILED, now, context, email_normalized, detail)

        assert user is not None

        if user.locked_until is not None and _aware(user.locked_until) > now:
            verify_dummy_password(password)
            await self._fail(
                AuthEventType.LOGIN_LOCKED, now, context, email_normalized, "locked", user=user
            )

        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            event_type = AuthEventType.LOGIN_FAILED
            detail = f"wrong password, attempt {user.failed_login_count}"
            if user.failed_login_count >= self.settings.LOGIN_MAX_FAILED_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=self.settings.LOGIN_LOCKOUT_MINUTES)
                user.failed_login_count = 0
                event_type = AuthEventType.LOGIN_LOCKED
                detail = "locked after repeated failures"
            await self._fail(event_type, now, context, email_normalized, detail, user=user)

        if not user.is_active:
            await self._fail(
                AuthEventType.LOGIN_FAILED, now, context, email_normalized, "inactive", user=user
            )

        memberships = await self.repository.list_active_memberships(user.id)
        if not memberships:
            await self._fail(
                AuthEventType.LOGIN_FAILED,
                now,
                context,
                email_normalized,
                "no active membership",
                user=user,
            )
        membership = memberships[0]
        organization = await self.repository.get_organization(membership.organization_id)
        assert organization is not None

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        token = generate_session_token()
        session = UserSession(
            user_id=user.id,
            organization_id=organization.id,
            token_hash=hash_session_token(token),
            expires_at=now + timedelta(hours=self.settings.SESSION_ABSOLUTE_LIFETIME_HOURS),
            last_seen_at=now,
            ip_address=_clip(context.ip_address, 45),
            user_agent=_clip(context.user_agent, 300),
        )
        self.repository.add(
            session,
            self._event(
                AuthEventType.LOGIN_SUCCEEDED,
                now,
                context,
                user=user,
                organization=organization,
            ),
        )
        await self.repository.commit()
        await self.repository.refresh(session)

        return token, AuthenticatedSession(user, organization, membership, session)

    # -- session validation ---------------------------------------------------------------

    async def authenticate(self, token: str | None) -> AuthenticatedSession:
        """Return the identity behind a session token, or raise SessionInvalidError."""

        if not token:
            raise SessionInvalidError("Sign in to continue.")

        session = await self.repository.get_session_by_token_hash(hash_session_token(token))
        if session is None or session.revoked_at is not None:
            raise SessionInvalidError("Sign in to continue.")

        now = self._now()
        idle_limit = timedelta(minutes=self.settings.SESSION_IDLE_TIMEOUT_MINUTES)
        if now >= _aware(session.expires_at) or now - _aware(session.last_seen_at) > idle_limit:
            session.revoked_at = now
            await self.repository.commit()
            raise SessionInvalidError("The session has expired. Sign in again.")

        user = await self.repository.get_user(session.user_id)
        organization = await self.repository.get_organization(session.organization_id)
        membership = await self.repository.get_membership(session.user_id, session.organization_id)
        if (
            user is None
            or not user.is_active
            or organization is None
            or not organization.is_active
            or membership is None
            or not membership.is_active
        ):
            session.revoked_at = now
            await self.repository.commit()
            raise SessionInvalidError("Sign in to continue.")

        if now - _aware(session.last_seen_at) >= LAST_SEEN_WRITE_INTERVAL:
            session.last_seen_at = now
            await self.repository.commit()

        return AuthenticatedSession(user, organization, membership, session)

    # -- sign-out -------------------------------------------------------------------------

    async def logout(self, token: str | None, context: RequestContext | None = None) -> None:
        """Revoke the session behind the token; an unknown or closed session is not an error."""

        if not token:
            return
        session = await self.repository.get_session_by_token_hash(hash_session_token(token))
        if session is None or session.revoked_at is not None:
            return

        now = self._now()
        session.revoked_at = now
        user = await self.repository.get_user(session.user_id)
        self.repository.add(
            self._event(AuthEventType.LOGOUT, now, context or RequestContext(), user=user)
        )
        await self.repository.commit()

    # -- password change ------------------------------------------------------------------

    async def change_password(
        self,
        identity: AuthenticatedSession,
        current_password: str,
        new_password: str,
        context: RequestContext | None = None,
    ) -> None:
        """Change the own password and close the user's other sessions."""

        user = identity.user
        if not verify_password(current_password, user.password_hash):
            raise PasswordChangeError("The current password is not correct.")
        if new_password == current_password:
            raise PasswordChangeError("The new password must differ from the current one.")
        validate_password_policy(new_password, email=user.email)

        now = self._now()
        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        user.must_change_password = False
        await self.repository.revoke_sessions_of_user(
            user.id, revoked_at=now, except_session_id=identity.session.id
        )
        self.repository.add(
            self._event(
                AuthEventType.PASSWORD_CHANGED,
                now,
                context or RequestContext(),
                user=user,
                organization=identity.organization,
            )
        )
        await self.repository.commit()

    # -- helpers --------------------------------------------------------------------------

    def _event(
        self,
        event_type: AuthEventType,
        occurred_at: datetime,
        context: RequestContext,
        *,
        user: User | None = None,
        organization: Organization | None = None,
        email_attempted: str | None = None,
        detail: str | None = None,
    ) -> AuthEvent:
        return AuthEvent(
            event_type=event_type,
            user_id=user.id if user is not None else None,
            organization_id=organization.id if organization is not None else None,
            email_attempted=_clip(email_attempted, 254),
            ip_address=_clip(context.ip_address, 45),
            user_agent=_clip(context.user_agent, 300),
            detail=_clip(detail, 300),
            occurred_at=occurred_at,
        )

    async def _fail(
        self,
        event_type: AuthEventType,
        now: datetime,
        context: RequestContext,
        email_attempted: str,
        detail: str,
        *,
        user: User | None = None,
    ) -> None:
        """Store the audit event together with any change to the user, then refuse."""

        self.repository.add(
            self._event(
                event_type, now, context, user=user, email_attempted=email_attempted, detail=detail
            )
        )
        await self.repository.commit()
        raise InvalidCredentialsError(self.sign_in_failed_message)


def _clip(value: str | None, length: int) -> str | None:
    return value[:length] if value else None


__all__ = [
    "AuthError",
    "AuthService",
    "AuthenticatedSession",
    "InvalidCredentialsError",
    "PasswordChangeError",
    "RequestContext",
    "SessionInvalidError",
]
