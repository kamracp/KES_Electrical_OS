// @vitest-environment node

import { describe, expect, it } from "vitest";

import {
  loadGroupRequestSchema,
  loadRunCreateRequestSchema,
} from "../services/loadDemand";
import { describeValidationIssue } from "../utils/validationMessages";
import {
  buildLoadRunPayload,
  createInitialLoadStudyDraft,
  createLoadRowDraft,
  createRowId,
  LOAD_STUDY_LABELS,
  loadStudyDraftSchema,
  seedRowIdCounter,
  type LoadRowDraft,
  type LoadStudyDraft,
} from "./loadStudyDraft";

function filledStudy(): LoadStudyDraft {
  const draft = createInitialLoadStudyDraft();
  draft.code = " LOAD-001 ";
  draft.name = " Process Pump Loads ";
  draft.coincidenceFactor = " 0.90 ";
  draft.loads = [threePhaseRow()];
  return draft;
}

function threePhaseRow(): LoadRowDraft {
  return {
    ...createLoadRowDraft(),
    code: " MTR-001 ",
    name: " Process Water Pump ",
    quantity: "2",
    ratedPowerKw: " 15 ",
    phaseSystem: "THREE_PHASE",
    voltageV: " 415 ",
    powerFactor: " 0.85 ",
    efficiency: "0.92",
    utilizationFactor: "0.80",
    demandFactor: "0.90",
    powerBasis: "MECHANICAL_OUTPUT",
  };
}

function dcRow(): LoadRowDraft {
  return {
    ...createLoadRowDraft(),
    code: "DC-001",
    name: "DC Control Load",
    quantity: "1",
    ratedPowerKw: "2.4",
    phaseSystem: "DC",
    voltageV: "48",
    utilizationFactor: "0.50",
    demandFactor: "0.75",
  };
}

describe("the initial load study draft", () => {
  it("starts with one empty load row and the IN profile", () => {
    const draft = createInitialLoadStudyDraft();

    expect(draft.loads).toHaveLength(1);
    expect(draft.jurisdictionProfile).toBe("IN");
    expect(draft.code).toBe("");
    expect(draft.coincidenceFactor).toBe("");
  });

  it("leaves the phase system for the engineer to choose", () => {
    const row = createLoadRowDraft();

    // The backend has no default phase system, so neither has the form: a
    // silent THREE_PHASE would decide the current calculation for the user.
    expect(row.phaseSystem).toBe("");
    // These two the backend does default, so the form may show them.
    expect(row.scenario).toBe("NORMAL");
    expect(row.powerBasis).toBe("ELECTRICAL_INPUT");
    expect(row.powerFactor).toBe("");
    expect(row.utilizationFactor).toBe("");
  });

  it("gives every row an id of its own", () => {
    const ids = [createRowId("load"), createRowId("load"), createLoadRowDraft().id];

    expect(new Set(ids).size).toBe(3);
  });
});

describe("loadStudyDraftSchema", () => {
  it("accepts the initial draft, a filled one and one kept through JSON", () => {
    expect(loadStudyDraftSchema.safeParse(createInitialLoadStudyDraft()).success).toBe(true);
    expect(loadStudyDraftSchema.safeParse(JSON.parse(JSON.stringify(filledStudy()))).success).toBe(
      true,
    );
  });

  it("refuses a draft with a field this form does not have", () => {
    const draft = { ...createInitialLoadStudyDraft(), unitRatings: [] };

    expect(loadStudyDraftSchema.safeParse(draft).success).toBe(false);
  });

  it("refuses a row with a missing field or a choice the contract does not know", () => {
    const { notes: _notes, ...rowWithoutNotes } = createLoadRowDraft();
    const unknownPhase = { ...createLoadRowDraft(), phaseSystem: "TWO_PHASE" };

    for (const row of [rowWithoutNotes, unknownPhase]) {
      const draft = { ...createInitialLoadStudyDraft(), loads: [row] };
      expect(loadStudyDraftSchema.safeParse(draft).success).toBe(false);
    }
  });

  it("refuses a draft without any load", () => {
    const draft = { ...createInitialLoadStudyDraft(), loads: [] };

    expect(loadStudyDraftSchema.safeParse(draft).success).toBe(false);
  });
});

describe("seedRowIdCounter", () => {
  it("moves the next id past every id in use", () => {
    seedRowIdCounter(["load-900", "load-902", "load-901"]);

    expect(createRowId("load")).toBe("load-903");
  });

  it("never moves the counter back and ignores ids of another form", () => {
    seedRowIdCounter(["load-950"]);
    seedRowIdCounter(["load-2", "rating-5000", "something"]);

    expect(createRowId("load")).toBe("load-951");
  });
});

describe("buildLoadRunPayload", () => {
  it("trims the text and sends the established factors as exact strings", () => {
    const payload = buildLoadRunPayload(filledStudy());
    const study = payload.study as Record<string, unknown>;
    const load = (study.loads as Record<string, unknown>[])[0];

    expect(study.code).toBe("LOAD-001");
    expect(study.name).toBe("Process Pump Loads");
    expect(study.coincidence_factor).toBe("0.90");
    expect(study.jurisdiction_profile).toBe("IN");
    expect(load.code).toBe("MTR-001");
    expect(load.rated_power_kw).toBe("15");
    expect(load.voltage_v).toBe("415");
    expect(load.power_factor).toBe("0.85");
    expect(load.quantity).toBe(2);
  });

  it("omits every blank optional instead of sending an empty string or 1", () => {
    const draft = createInitialLoadStudyDraft();
    draft.code = "LOAD-002";
    draft.name = "Unestablished Factors";
    draft.loads = [
      { ...createLoadRowDraft(), code: "MTR-002", name: "Pump", quantity: "1",
        ratedPowerKw: "15", phaseSystem: "THREE_PHASE", voltageV: "415", powerFactor: "0.85" },
    ];

    const payload = buildLoadRunPayload(draft);
    const study = payload.study as Record<string, unknown>;
    const load = (study.loads as Record<string, unknown>[])[0];

    // A15 (a): a blank factor means NOT ESTABLISHED and must reach the engine
    // as an absent key, never as "" and never as "1".
    expect(Object.keys(study)).not.toContain("coincidence_factor");
    expect(Object.keys(load)).not.toContain("efficiency");
    expect(Object.keys(load)).not.toContain("utilization_factor");
    expect(Object.keys(load)).not.toContain("demand_factor");
    expect(Object.keys(load)).not.toContain("notes");
    expect(Object.keys(payload)).not.toContain("notes");
  });

  it("omits a blank power factor so the DC rule and the AC rule can decide", () => {
    const draft = createInitialLoadStudyDraft();
    draft.loads = [dcRow()];

    const load = ((buildLoadRunPayload(draft).study as Record<string, unknown>)
      .loads as Record<string, unknown>[])[0];

    expect(Object.keys(load)).not.toContain("power_factor");
  });

  it("sends the project revision only when one is given", () => {
    const revisionId = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";

    expect(Object.keys(buildLoadRunPayload(filledStudy()))).not.toContain("project_revision_id");
    expect(buildLoadRunPayload(filledStudy(), revisionId).project_revision_id).toBe(revisionId);
  });

  it("sends the study notes only when they are written", () => {
    const draft = filledStudy();
    draft.notes = "  Preliminary schedule.  ";

    expect(buildLoadRunPayload(draft).notes).toBe("Preliminary schedule.");
  });

  it("passes a quantity that is not a whole number through as typed", () => {
    const draft = filledStudy();
    draft.loads = [{ ...threePhaseRow(), quantity: "2.5" }];

    const load = ((buildLoadRunPayload(draft).study as Record<string, unknown>)
      .loads as Record<string, unknown>[])[0];

    // Left as the string the user typed, so the schema reports it instead of
    // this builder guessing what was meant.
    expect(load.quantity).toBe("2.5");
  });
});

describe("the payload the form will send", () => {
  it("is accepted by the run request schema for a three-phase and a DC row", () => {
    const draft = filledStudy();
    draft.loads = [threePhaseRow(), dcRow()];

    const parsed = loadRunCreateRequestSchema.safeParse(buildLoadRunPayload(draft));

    expect(parsed.success).toBe(true);
  });

  it("is accepted by the group schema once the study is taken out of it", () => {
    const payload = buildLoadRunPayload(filledStudy());

    expect(loadGroupRequestSchema.safeParse(payload.study).success).toBe(true);
  });

  it("names the row and the field when an AC load carries no power factor", () => {
    const draft = filledStudy();
    draft.loads = [threePhaseRow(), { ...threePhaseRow(), code: "MTR-002", powerFactor: "" }];

    const parsed = loadRunCreateRequestSchema.safeParse(buildLoadRunPayload(draft));

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      expect(issue.path).toEqual(["study", "loads", 1, "power_factor"]);
      // The rule reports a missing value, so the reader sees the form's own
      // label and a plain sentence - no schema wording and no raw field name.
      expect(describeValidationIssue(issue, LOAD_STUDY_LABELS)).toBe(
        "Load 2 — Power factor is required.",
      );
    }
  });

  it("names the row and the field for an ordinary missing value", () => {
    const draft = filledStudy();
    draft.loads = [{ ...threePhaseRow(), ratedPowerKw: "" }];

    const parsed = loadRunCreateRequestSchema.safeParse(buildLoadRunPayload(draft));

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(describeValidationIssue(parsed.error.issues[0], LOAD_STUDY_LABELS)).toBe(
        "Load 1 — Rated power (kW) is required.",
      );
    }
  });
});

describe("LOAD_STUDY_LABELS", () => {
  it("keys every label by a path the request schema really has", () => {
    const study = Object.keys(loadGroupRequestSchema.shape);
    const run = Object.keys(loadRunCreateRequestSchema.shape);
    const row = Object.keys(loadGroupRequestSchema.shape.loads.element.shape);

    for (const key of Object.keys(LOAD_STUDY_LABELS.fields)) {
      if (key.startsWith("study.loads.*.")) {
        expect(row).toContain(key.slice("study.loads.*.".length));
      } else if (key.startsWith("study.")) {
        expect(study).toContain(key.slice("study.".length));
      } else {
        expect(run).toContain(key);
      }
    }
  });

  it("names a load row in the singular", () => {
    expect(LOAD_STUDY_LABELS.groups?.loads).toBe("Load");
  });
});
