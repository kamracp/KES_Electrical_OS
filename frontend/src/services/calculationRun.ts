import { z } from "zod";

import { projectRevisionSummarySchema } from "./projects";

// Traceability record of one persisted calculation run (Master Prompt v2.1
// item 15 / section 19). The backend keeps every module's runs in one generic
// table, so this summary is shared by all study pages and never belongs to a
// single module's service.
export const calculationRunSummarySchema = z
  .object({
    id: z.string().uuid(),
    // The project revision the run belongs to, and the names behind that id; both are null
    // for a run made outside any project (EOS-01 b).
    project_revision_id: z.string().uuid().nullable(),
    project: projectRevisionSummarySchema.nullable(),
    module_code: z.string(),
    calculation_type: z.string(),
    calculation_key: z.string(),
    revision_number: z.number().int(),
    run_status: z.string(),
    approval_status: z.string(),
    engine_version: z.string(),
    design_check_status: z.string(),
    jurisdiction_profile: z.string(),
    reference_verification_status: z.string(),
    content_hash: z.string().length(64),
    calculated_by: z.string().nullable(),
    calculated_at: z.string(),
    created_at: z.string(),
    is_immutable: z.boolean(),
    supersedes_run_id: z.string().uuid().nullable(),
    notes: z.string().nullable(),
  })
  .strict();

export type CalculationRunSummary = z.infer<typeof calculationRunSummarySchema>;
