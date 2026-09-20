import { z } from "zod";

import { ApiError, describeApiError, requestJson } from "./http";

// Sign-in, sign-out, the current session and password change (EOS-01 a).
//
// The session token lives only in an HttpOnly cookie set by the server: this code never
// sees it, never stores it, and nothing here touches localStorage or sessionStorage.

export const organizationRoleSchema = z.enum(["OWNER", "ENGINEER", "VIEWER"]);

export const sessionSchema = z
  .object({
    user: z
      .object({
        id: z.string().uuid(),
        email: z.string(),
        full_name: z.string(),
        must_change_password: z.boolean(),
      })
      .strict(),
    organization: z
      .object({
        id: z.string().uuid(),
        code: z.string(),
        name: z.string(),
      })
      .strict(),
    role: organizationRoleSchema,
    session_expires_at: z.string(),
    idle_timeout_minutes: z.number().int().positive(),
  })
  .strict();

export type OrganizationRole = z.infer<typeof organizationRoleSchema>;
export type Session = z.infer<typeof sessionSchema>;

const AUTH = "/api/v1/auth";

function parseSession(data: unknown): Session {
  const parsed = sessionSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS sign-in API.");
  }

  return parsed.data;
}

/** The signed-in session, or null when nobody is signed in (HTTP 401). */
export async function getSession(signal?: AbortSignal): Promise<Session | null> {
  const response = await requestJson(`${AUTH}/me`, { method: "GET", signal });

  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new ApiError(
      describeApiError(response.data, response.status, "The session could not be checked"),
      response.status,
    );
  }

  return parseSession(response.data);
}

/** Sign in; on success the server sets the session cookie and returns the session. */
export async function signIn(email: string, password: string): Promise<Session> {
  const response = await requestJson(`${AUTH}/login`, {
    method: "POST",
    body: { email, password },
  });

  if (!response.ok) {
    throw new ApiError(
      describeApiError(response.data, response.status, "Sign-in failed"),
      response.status,
    );
  }

  return parseSession(response.data);
}

/** Close the session on the server; the server also removes the cookie. */
export async function signOut(): Promise<void> {
  const response = await requestJson(`${AUTH}/logout`, { method: "POST" });

  if (!response.ok) {
    throw new ApiError(
      describeApiError(response.data, response.status, "Sign-out failed"),
      response.status,
    );
  }
}

/** Change the own password; the server closes this user's other sessions. */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await requestJson(`${AUTH}/password`, {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });

  if (!response.ok) {
    throw new ApiError(
      describeApiError(response.data, response.status, "The password was not changed"),
      response.status,
    );
  }
}
