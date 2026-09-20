"""
Create the first owner of an organization, or recover owner access (EOS-01 a).

Run on the server, from the backend directory so that .env is found:

    cd /opt/kes-electrical-os/backend
    ../.venv/bin/python -m app.cli.create_owner
    ../.venv/bin/python -m app.cli.create_owner --recover

The password is always asked for at the terminal without echo. It is never taken from the
command line or from an environment variable, so it cannot end up in the shell history or in
a process list.
"""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.engine import AsyncSessionFactory
from app.repositories.identity import IdentityRepository
from app.services.owner_bootstrap import (
    OwnerBootstrapError,
    OwnerBootstrapResult,
    OwnerBootstrapService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.create_owner",
        description="Create the first owner of an organization, or recover owner access.",
    )
    parser.add_argument("--organization-code", help="short code, for example KES")
    parser.add_argument("--organization-name", help="full name; used when the code is new")
    parser.add_argument("--email", help="sign-in e-mail of the owner")
    parser.add_argument("--full-name", help="name of the owner")
    parser.add_argument(
        "--recover",
        action="store_true",
        help="give an existing user owner access back and set a new password",
    )
    return parser


def _ask(value: str | None, prompt: str) -> str:
    return value if value is not None else input(f"{prompt}: ")


def _ask_password() -> str | None:
    first = getpass.getpass("Password (12 characters or more, not shown): ")
    second = getpass.getpass("Password again: ")
    return first if first == second else None


async def run(
    args: argparse.Namespace,
    password: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> OwnerBootstrapResult:
    async with session_factory() as db:
        service = OwnerBootstrapService(IdentityRepository(db))
        if args.recover:
            return await service.recover_owner(
                organization_code=args.organization_code,
                email=args.email,
                password=password,
            )
        return await service.create_owner(
            organization_code=args.organization_code,
            organization_name=args.organization_name,
            email=args.email,
            full_name=args.full_name,
            password=password,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.organization_code = _ask(args.organization_code, "Organization code (for example KES)")
    if not args.recover:
        args.organization_name = _ask(args.organization_name, "Organization name")
    args.email = _ask(args.email, "Owner e-mail")
    if not args.recover:
        args.full_name = _ask(args.full_name, "Owner full name")

    password = _ask_password()
    if password is None:
        print("The two passwords differ; nothing was changed.", file=sys.stderr)
        return 1

    try:
        result = asyncio.run(run(args, password, AsyncSessionFactory))
    except OwnerBootstrapError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1

    organization = "new organization" if result.organization_created else "organization"
    print(f"Owner {result.action}: {result.email} in {organization} {result.organization_code}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
