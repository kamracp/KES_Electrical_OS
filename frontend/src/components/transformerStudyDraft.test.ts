// @vitest-environment node

import { describe, expect, it } from "vitest";

import {
  transformerRunCreateRequestSchema,
  transformerSizingRequestSchema,
} from "../services/transformerSizing";
import { describeValidationIssue } from "../utils/validationMessages";
import {
  buildTransformerRunPayload,
  createInitialTransformerStudyDraft,
  deriveStandbyUnits,
  createRatingId,
  createUnitRatingDraft,
  seedRatingIdCounter,
  transformerStudyDraftSchema,
  TRANSFORMER_STUDY_LABELS,
  type TransformerStudyDraft,
} from "./transformerStudyDraft";

const FACTOR_KEYS = [
  "future_growth_factor",
  "design_margin_factor",
  "ambient_derating_factor",
  "altitude_derating_factor",
  "harmonic_derating_factor",
];

function filledStudy(): TransformerStudyDraft {
  const draft = createInitialTransformerStudyDraft();
  draft.code = " TR-001 ";
  draft.name = " Main Transformer ";
  draft.demandPowerKw = " 800 ";
  draft.demandPowerFactor = " 0.80 ";
  draft.unitRatings = [
    { ...createUnitRatingDraft(), value: " 1000 " },
    { ...createUnitRatingDraft(), value: "1250" },
    { ...createUnitRatingDraft(), value: "1600" },
  ];
  return draft;
}

function study(payload: Record<string, unknown>): Record<string, unknown> {
  return payload.study as Record<string, unknown>;
}

describe("the initial transformer study draft", () => {
  it("starts with one empty rating entry and the backend's own defaults", () => {
    const draft = createInitialTransformerStudyDraft();

    expect(draft.unitRatings).toHaveLength(1);
    expect(draft.unitRatings[0].value).toBe("");
    expect(draft.jurisdictionProfile).toBe("IN");
    expect(draft.scenario).toBe("NORMAL");
    expect(draft.redundancyMode).toBe("NONE");
    expect(draft.dutyUnits).toBe("1");
    expect(draft.standbyUnits).toBe("0");
  });

  it("leaves every factor and the power factor for the engineer", () => {
    const draft = createInitialTransformerStudyDraft();

    expect(draft.demandPowerFactor).toBe("");
    expect(draft.designMarginFactor).toBe("");
    expect(draft.futureGrowthFactor).toBe("");
  });

  it("gives every rating entry an id of its own", () => {
    const ids = [createRatingId(), createRatingId(), createUnitRatingDraft().id];

    expect(new Set(ids).size).toBe(3);
  });
});

describe("transformerStudyDraftSchema", () => {
  it("accepts the initial draft and a draft kept through JSON", () => {
    const draft = createInitialTransformerStudyDraft();

    expect(transformerStudyDraftSchema.safeParse(draft).success).toBe(true);
    expect(transformerStudyDraftSchema.safeParse(JSON.parse(JSON.stringify(draft))).success).toBe(
      true,
    );
  });

  it("refuses a draft with a field this form does not have", () => {
    const draft = { ...createInitialTransformerStudyDraft(), loadRows: [] };

    expect(transformerStudyDraftSchema.safeParse(draft).success).toBe(false);
  });

  it("refuses a draft with a missing field or a choice the contract does not know", () => {
    const { notes: _notes, ...withoutNotes } = createInitialTransformerStudyDraft();
    const unknownMode = { ...createInitialTransformerStudyDraft(), redundancyMode: "N_PLUS_2" };

    expect(transformerStudyDraftSchema.safeParse(withoutNotes).success).toBe(false);
    expect(transformerStudyDraftSchema.safeParse(unknownMode).success).toBe(false);
  });

  it("refuses a draft without any rating entry", () => {
    const draft = { ...createInitialTransformerStudyDraft(), unitRatings: [] };

    expect(transformerStudyDraftSchema.safeParse(draft).success).toBe(false);
  });
});

describe("seedRatingIdCounter", () => {
  it("moves the next id past every id in use", () => {
    seedRatingIdCounter(["rating-900", "rating-902", "rating-901"]);

    expect(createRatingId()).toBe("rating-903");
  });

  it("never moves the counter back and ignores ids of another form", () => {
    seedRatingIdCounter(["rating-950"]);
    seedRatingIdCounter(["rating-2", "load-5000", "something"]);

    expect(createRatingId()).toBe("rating-951");
  });
});

describe("deriveStandbyUnits", () => {
  it("gives the standby count each redundancy mode requires", () => {
    // The backend refuses any other combination
    // (schemas/transformer_sizing.py), so the form derives it instead.
    expect(deriveStandbyUnits("NONE", "2")).toBe("0");
    expect(deriveStandbyUnits("N_PLUS_1", "2")).toBe("1");
    expect(deriveStandbyUnits("TWO_N", "2")).toBe("2");
  });

  it("follows the duty units under 2N", () => {
    expect(deriveStandbyUnits("TWO_N", "1")).toBe("1");
    expect(deriveStandbyUnits("TWO_N", "3")).toBe("3");
  });

  it("passes a bad duty value through under 2N, so it is reported once", () => {
    // Reported against Duty units, not twice against Standby units as well.
    expect(deriveStandbyUnits("TWO_N", "")).toBe("");
    expect(deriveStandbyUnits("TWO_N", "1.5")).toBe("1.5");
  });

  it("ignores the duty units when the mode does not use them", () => {
    expect(deriveStandbyUnits("NONE", "4")).toBe("0");
    expect(deriveStandbyUnits("N_PLUS_1", "4")).toBe("1");
  });
});

describe("buildTransformerRunPayload", () => {
  it("trims the text and keeps the ratings in the order they are on screen", () => {
    const payload = buildTransformerRunPayload(filledStudy());
    const built = study(payload);

    expect(built.code).toBe("TR-001");
    expect(built.name).toBe("Main Transformer");
    expect(built.demand_power_kw).toBe("800");
    expect(built.demand_power_factor).toBe("0.80");
    expect(built.available_unit_ratings_kva).toEqual(["1000", "1250", "1600"]);
    expect(built.duty_units).toBe(1);
    expect(built.standby_units).toBe(0);
  });

  it("never reorders a schedule the engineer typed out of order", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1250" },
      { ...createUnitRatingDraft(), value: "1000" },
    ];

    // The backend requires a unique ascending schedule and must be the one to
    // say so; sorting here would hide the engineer's mistake.
    expect(study(buildTransformerRunPayload(draft)).available_unit_ratings_kva).toEqual([
      "1250",
      "1000",
    ]);
  });

  it("omits every blank optional instead of sending an empty string or 1", () => {
    const built = study(buildTransformerRunPayload(filledStudy()));

    // A16 (a): a blank factor means NOT ESTABLISHED and must reach the engine
    // as an absent key, never as "" and never as "1".
    for (const key of FACTOR_KEYS) {
      expect(Object.keys(built)).not.toContain(key);
    }
    expect(Object.keys(buildTransformerRunPayload(filledStudy()))).not.toContain("notes");
  });

  it("sends the factors that are established", () => {
    const draft = filledStudy();
    draft.designMarginFactor = " 1.10 ";
    draft.ambientDeratingFactor = "0.95";

    const built = study(buildTransformerRunPayload(draft));

    expect(built.design_margin_factor).toBe("1.10");
    expect(built.ambient_derating_factor).toBe("0.95");
    expect(Object.keys(built)).not.toContain("future_growth_factor");
  });

  it("sends a blank rating entry too, so the numbering matches the screen", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1000" },
      { ...createUnitRatingDraft(), value: "  " },
      { ...createUnitRatingDraft(), value: "1250" },
    ];

    // Dropping the blank would make the third entry index 1, so a message about
    // it would say "Unit rating 2" while the screen shows rating 3.
    expect(study(buildTransformerRunPayload(draft)).available_unit_ratings_kva).toEqual([
      "1000",
      "",
      "1250",
    ]);
  });

  it("sends the project revision and the notes only when they are given", () => {
    const revisionId = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";
    const draft = filledStudy();
    draft.notes = "  Preliminary sizing.  ";

    expect(Object.keys(buildTransformerRunPayload(filledStudy()))).not.toContain(
      "project_revision_id",
    );
    expect(buildTransformerRunPayload(draft, revisionId).project_revision_id).toBe(revisionId);
    expect(buildTransformerRunPayload(draft).notes).toBe("Preliminary sizing.");
  });

  it("passes a unit count that is not a whole number through as typed", () => {
    const draft = filledStudy();
    draft.dutyUnits = "1.5";

    expect(study(buildTransformerRunPayload(draft)).duty_units).toBe("1.5");
  });

  it("sends the derived standby count, never the one held in the draft", () => {
    const draft = filledStudy();
    draft.redundancyMode = "TWO_N";
    draft.dutyUnits = "2";
    // Even if the draft field fell out of step, the payload follows the rule.
    draft.standbyUnits = "99";

    expect(study(buildTransformerRunPayload(draft)).standby_units).toBe(2);
  });

  it("sends a bad duty value as the standby count too under 2N", () => {
    const draft = filledStudy();
    draft.redundancyMode = "TWO_N";
    draft.dutyUnits = "";

    const built = study(buildTransformerRunPayload(draft));

    expect(built.duty_units).toBe("");
    expect(built.standby_units).toBe("");
  });
});

describe("the payload the form will send", () => {
  it("is accepted by the run request schema", () => {
    expect(
      transformerRunCreateRequestSchema.safeParse(buildTransformerRunPayload(filledStudy()))
        .success,
    ).toBe(true);
  });

  it("is accepted by the study schema once the study is taken out of it", () => {
    const payload = buildTransformerRunPayload(filledStudy());

    expect(transformerSizingRequestSchema.safeParse(payload.study).success).toBe(true);
  });

  it("names the power factor when it is missing", () => {
    const draft = filledStudy();
    draft.demandPowerFactor = "";

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const issue = parsed.error.issues.find(
        (candidate) => candidate.path.at(-1) === "demand_power_factor",
      );
      expect(describeValidationIssue(issue!, TRANSFORMER_STUDY_LABELS)).toBe(
        "Power factor is required.",
      );
    }
  });

  it("names the rating entry the engineer mistyped", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1000" },
      { ...createUnitRatingDraft(), value: "1250 kVA" },
    ];

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      expect(issue.path).toEqual(["study", "available_unit_ratings_kva", 1]);
      expect(describeValidationIssue(issue, TRANSFORMER_STUDY_LABELS)).toContain(
        "Unit rating 2",
      );
    }
  });

  it("names the blank entry by its position on screen", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1000" },
      { ...createUnitRatingDraft(), value: "  " },
      { ...createUnitRatingDraft(), value: "1250" },
    ];

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      expect(issue.path).toEqual(["study", "available_unit_ratings_kva", 1]);
      expect(describeValidationIssue(issue, TRANSFORMER_STUDY_LABELS)).toBe(
        "Unit rating 2 is required.",
      );
    }
  });

  it("names the entry that breaks the ascending order", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1000" },
      { ...createUnitRatingDraft(), value: "1250" },
      { ...createUnitRatingDraft(), value: "1250" },
    ];

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      // A repeat is neither unique nor ascending; the third entry is the first
      // one that breaks the rule, so that is the one named.
      expect(describeValidationIssue(parsed.error.issues[0], TRANSFORMER_STUDY_LABELS)).toBe(
        "Unit rating 3: Ratings must be unique and in ascending order.",
      );
    }
  });

  it("names the entry that goes backwards", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1250" },
      { ...createUnitRatingDraft(), value: "1000" },
    ];

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(describeValidationIssue(parsed.error.issues[0], TRANSFORMER_STUDY_LABELS)).toBe(
        "Unit rating 2: Ratings must be unique and in ascending order.",
      );
    }
  });

  it("accepts a schedule that ascends", () => {
    const draft = filledStudy();
    draft.unitRatings = [
      { ...createUnitRatingDraft(), value: "1000" },
      { ...createUnitRatingDraft(), value: "1250" },
      { ...createUnitRatingDraft(), value: "1600" },
    ];

    expect(
      transformerRunCreateRequestSchema.safeParse(buildTransformerRunPayload(draft)).success,
    ).toBe(true);
  });

  it("asks for at least one rating when the schedule has no entry at all", () => {
    const draft = filledStudy();
    draft.unitRatings = [];

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(describeValidationIssue(parsed.error.issues[0], TRANSFORMER_STUDY_LABELS)).toBe(
        "Unit ratings needs at least 1 entry.",
      );
    }
  });
});

describe("TRANSFORMER_STUDY_LABELS", () => {
  it("keys every label by a path the request schema really has", () => {
    const run = Object.keys(transformerRunCreateRequestSchema.shape);
    // The study schema carries a superRefine; in zod 4 that keeps the object
    // shape in place rather than wrapping it, so def.shape is the field list.
    const fields = Object.keys(
      (transformerSizingRequestSchema.def as { shape: Record<string, unknown> }).shape,
    );

    expect(fields.length).toBeGreaterThan(0);
    for (const key of Object.keys(TRANSFORMER_STUDY_LABELS.fields)) {
      if (key.startsWith("study.")) {
        expect(fields).toContain(key.slice("study.".length));
      } else {
        expect(run).toContain(key);
      }
    }
  });

  it("names a rating entry in the singular", () => {
    expect(TRANSFORMER_STUDY_LABELS.groups?.available_unit_ratings_kva).toBe("Unit rating");
  });
});
