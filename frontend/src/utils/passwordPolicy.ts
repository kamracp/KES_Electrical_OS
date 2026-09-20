// The rule for a NEW password, mirrored from the server (backend app/core/security.py) so a
// form can answer at once. The server applies the rule again and stays the authority.
// Length is what counts: there are no composition rules and a passphrase with spaces is welcome.

export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 128;

/** A sentence naming what is wrong with a new password, or null when it is acceptable. */
export function describePasswordProblem(
  password: string,
  email: string,
  label: string,
): string | null {
  if (password === "") {
    return `${label} is required.`;
  }
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `${label} must have at least ${PASSWORD_MIN_LENGTH} characters.`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `${label} must have at most ${PASSWORD_MAX_LENGTH} characters.`;
  }
  if (password.trim() === "") {
    return `${label} must not be blank.`;
  }
  if (email.trim() !== "" && password.toLowerCase() === email.trim().toLowerCase()) {
    return `${label} must not be the e-mail address.`;
  }
  return null;
}
