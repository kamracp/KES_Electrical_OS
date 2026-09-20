import { z } from "zod";

import { organizationRoleSchema, type OrganizationRole } from "./auth";
import { ApiError, describeApiError, requestJson } from "./http";

// User administration for the owner of an organization (EOS-01 a). Every route below is
// owner-only on the server; another role gets HTTP 403. Users are never deleted: an account
// is switched off, so the names on old calculation runs and audit records keep their meaning.

export const userSchema = z
  .object({
    id: z.string().uuid(),
    email: z.string(),
    full_name: z.string(),
    role: organizationRoleSchema,
    is_active: z.boolean(),
    must_change_password: z.boolean(),
    locked_until: z.string().nullable(),
    last_login_at: z.string().nullable(),
  })
  .strict();

const userListSchema = z.object({ items: z.array(userSchema), total: z.number().int() }).strict();

export const authEventTypeSchema = z.enum([
  "LOGIN_SUCCEEDED",
  "LOGIN_FAILED",
  "LOGIN_LOCKED",
  "LOGOUT",
  "USER_CREATED",
  "USER_UPDATED",
  "PASSWORD_CHANGED",
  "PASSWORD_RESET",
]);

export const authEventSchema = z
  .object({
    id: z.string().uuid(),
    event_type: authEventTypeSchema,
    user_id: z.string().uuid().nullable(),
    email_attempted: z.string().nullable(),
    ip_address: z.string().nullable(),
    user_agent: z.string().nullable(),
    detail: z.string().nullable(),
    occurred_at: z.string(),
  })
  .strict();

const authEventListSchema = z.object({ items: z.array(authEventSchema) }).strict();

export type User = z.infer<typeof userSchema>;
export type AuthEventType = z.infer<typeof authEventTypeSchema>;
export type AuthEvent = z.infer<typeof authEventSchema>;

export type NewUser = {
  email: string;
  full_name: string;
  role: OrganizationRole;
  password: string;
};

/** Only the fields that are given are changed. */
export type UserChange = {
  full_name?: string;
  role?: OrganizationRole;
  is_active?: boolean;
};

const USERS = "/api/v1/users";
const UNEXPECTED = "Unexpected response from the KES Electrical OS users API.";

function refusal(data: unknown, status: number, fallback: string): ApiError {
  return new ApiError(describeApiError(data, status, fallback), status);
}

function parseUser(data: unknown): User {
  const parsed = userSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error(UNEXPECTED);
  }

  return parsed.data;
}

/** Every user of the owner's organization, switched off or not. */
export async function listUsers(signal?: AbortSignal): Promise<User[]> {
  const response = await requestJson(USERS, { method: "GET", signal });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The user list could not be loaded");
  }

  const parsed = userListSchema.safeParse(response.data);

  if (!parsed.success) {
    throw new Error(UNEXPECTED);
  }

  return parsed.data.items;
}

/** The sign-in and user-administration audit trail, newest first. */
export async function listAuthEvents(limit = 50, signal?: AbortSignal): Promise<AuthEvent[]> {
  const response = await requestJson(`${USERS}/events?limit=${limit}`, { method: "GET", signal });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The audit trail could not be loaded");
  }

  const parsed = authEventListSchema.safeParse(response.data);

  if (!parsed.success) {
    throw new Error(UNEXPECTED);
  }

  return parsed.data.items;
}

/** Create a user with a first password that must be changed at the first sign-in. */
export async function createUser(user: NewUser): Promise<User> {
  const response = await requestJson(USERS, {
    method: "POST",
    body: { ...user, must_change_password: true },
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The user was not created");
  }

  return parseUser(response.data);
}

/** Rename, change the role, switch off or switch on; switching off closes the sessions. */
export async function updateUser(userId: string, change: UserChange): Promise<User> {
  const response = await requestJson(`${USERS}/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: change,
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The user was not changed");
  }

  return parseUser(response.data);
}

/** Set a new first password; the user's sessions are closed and a change is required. */
export async function resetUserPassword(userId: string, newPassword: string): Promise<void> {
  const response = await requestJson(`${USERS}/${encodeURIComponent(userId)}/password`, {
    method: "POST",
    body: { new_password: newPassword },
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The password was not reset");
  }
}
