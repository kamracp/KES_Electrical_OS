import type { OrganizationRole } from "../services/auth";

// On-screen names of the organization roles. The Record type makes this exhaustive: a role
// added to the contract without a label here stops the type check.
export const ROLE_LABELS: Record<OrganizationRole, string> = {
  OWNER: "Owner",
  ENGINEER: "Engineer",
  VIEWER: "Viewer",
};
