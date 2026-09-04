import { useState, type FormEvent } from "react";

import {
  shortCircuitStudyRequestSchema,
  type ShortCircuitStudyRequest,
} from "../services/fault";

type FaultStudyFormProps = {
  disabled?: boolean;
  onSubmit: (payload: ShortCircuitStudyRequest) => void | Promise<void>;
};

type FaultStudyDraft = {
  studyCode: string;
  studyName: string;
  calculationCase: string;
  faultBusCode: string;
  faultBusName: string;
  faultType: string;
  nominalVoltageV: string;
  voltageFactorMax: string;
  voltageFactorMin: string;
  neutralEarthingMode: string;
  neutralResistanceOhm: string;
  neutralReactanceOhm: string;
  sourceCode: string;
  sourceName: string;
  sourceType: string;
  sourceRepresentation: string;
  sourceResistanceOhm: string;
  sourceReactanceOhm: string;
  currentContributionKa: string;
  frequencyHz: string;
};

const initialDraft: FaultStudyDraft = {
  studyCode: "",
  studyName: "",
  calculationCase: "",
  faultBusCode: "",
  faultBusName: "",
  faultType: "",
  nominalVoltageV: "",
  voltageFactorMax: "",
  voltageFactorMin: "",
  neutralEarthingMode: "",
  neutralResistanceOhm: "",
  neutralReactanceOhm: "",
  sourceCode: "",
  sourceName: "",
  sourceType: "",
  sourceRepresentation: "",
  sourceResistanceOhm: "",
  sourceReactanceOhm: "",
  currentContributionKa: "",
  frequencyHz: "",
};

export function FaultStudyForm({ disabled = false, onSubmit }: FaultStudyFormProps) {
  const [draft, setDraft] = useState<FaultStudyDraft>(initialDraft);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateField<K extends keyof FaultStudyDraft>(
    field: K,
    value: FaultStudyDraft[K],
  ) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const payload = {
      code: draft.studyCode,
      name: draft.studyName,
      calculation_case: draft.calculationCase,
      fault: {
        bus_code: draft.faultBusCode,
        fault_type: draft.faultType,
      },
      buses: [
        {
          code: draft.faultBusCode,
          name: draft.faultBusName,
          nominal_voltage_v: draft.nominalVoltageV,
          voltage_factor_max: draft.voltageFactorMax,
          voltage_factor_min: draft.voltageFactorMin,
          neutral_earthing_mode: draft.neutralEarthingMode,
          neutral_resistance_ohm: draft.neutralResistanceOhm || undefined,
          neutral_reactance_ohm: draft.neutralReactanceOhm || undefined,
        },
      ],
      sources: [
        {
          code: draft.sourceCode,
          name: draft.sourceName,
          bus_code: draft.faultBusCode,
          source_type: draft.sourceType,
          representation: draft.sourceRepresentation,
          ...(draft.sourceRepresentation === "VOLTAGE_BEHIND_IMPEDANCE"
            ? {
                positive_sequence_impedance: {
                  resistance_ohm: draft.sourceResistanceOhm,
                  reactance_ohm: draft.sourceReactanceOhm,
                },
              }
            : {}),
          ...(draft.sourceRepresentation === "CURRENT_INJECTION"
            ? { current_contribution_ka: draft.currentContributionKa }
            : {}),
        },
      ],
      frequency_hz: draft.frequencyHz || undefined,
    };

    const parsed = shortCircuitStudyRequestSchema.safeParse(payload);

    if (!parsed.success) {
      setValidationError(
        parsed.error.issues[0]?.message ?? "Review the fault-study inputs.",
      );
      return;
    }

    await onSubmit(parsed.data);
  }

  const usesImpedance = draft.sourceRepresentation === "VOLTAGE_BEHIND_IMPEDANCE";
  const usesCurrentInjection = draft.sourceRepresentation === "CURRENT_INJECTION";

  return (
    <form aria-label="Fault study inputs" onSubmit={handleSubmit}>
      <fieldset disabled={disabled}>
        <legend>Study definition</legend>

        <label>
          Study code
          <input
            name="studyCode"
            value={draft.studyCode}
            onChange={(event) => updateField("studyCode", event.target.value)}
          />
        </label>

        <label>
          Study name
          <input
            name="studyName"
            value={draft.studyName}
            onChange={(event) => updateField("studyName", event.target.value)}
          />
        </label>

        <label>
          Calculation case
          <select
            name="calculationCase"
            value={draft.calculationCase}
            onChange={(event) => updateField("calculationCase", event.target.value)}
          >
            <option value="">Select case</option>
            <option value="MAXIMUM">Maximum</option>
            <option value="MINIMUM">Minimum</option>
          </select>
        </label>

        <label>
          Fault type
          <select
            name="faultType"
            value={draft.faultType}
            onChange={(event) => updateField("faultType", event.target.value)}
          >
            <option value="">Select fault type</option>
            <option value="THREE_PHASE">Three-phase</option>
            <option value="TWO_PHASE">Phase-to-phase</option>
            <option value="TWO_PHASE_TO_EARTH">Phase-to-phase-to-earth</option>
            <option value="SINGLE_PHASE_TO_EARTH">Single-phase-to-earth</option>
          </select>
        </label>

        <label>
          Frequency (Hz)
          <input
            inputMode="decimal"
            name="frequencyHz"
            value={draft.frequencyHz}
            onChange={(event) => updateField("frequencyHz", event.target.value)}
          />
        </label>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Fault bus</legend>

        <label>
          Bus code
          <input
            name="faultBusCode"
            value={draft.faultBusCode}
            onChange={(event) => updateField("faultBusCode", event.target.value)}
          />
        </label>

        <label>
          Bus name
          <input
            name="faultBusName"
            value={draft.faultBusName}
            onChange={(event) => updateField("faultBusName", event.target.value)}
          />
        </label>

        <label>
          Nominal voltage (V)
          <input
            inputMode="decimal"
            name="nominalVoltageV"
            value={draft.nominalVoltageV}
            onChange={(event) => updateField("nominalVoltageV", event.target.value)}
          />
        </label>

        <label>
          Maximum voltage factor
          <input
            inputMode="decimal"
            name="voltageFactorMax"
            value={draft.voltageFactorMax}
            onChange={(event) => updateField("voltageFactorMax", event.target.value)}
          />
        </label>

        <label>
          Minimum voltage factor
          <input
            inputMode="decimal"
            name="voltageFactorMin"
            value={draft.voltageFactorMin}
            onChange={(event) => updateField("voltageFactorMin", event.target.value)}
          />
        </label>

        <label>
          Neutral earthing mode
          <select
            name="neutralEarthingMode"
            value={draft.neutralEarthingMode}
            onChange={(event) =>
              updateField("neutralEarthingMode", event.target.value)
            }
          >
            <option value="">Select earthing mode</option>
            <option value="SOLIDLY_EARTHED">Solidly earthed</option>
            <option value="RESISTANCE_EARTHED">Resistance earthed</option>
            <option value="REACTANCE_EARTHED">Reactance earthed</option>
            <option value="RESONANT_EARTHED">Resonant earthed</option>
            <option value="ISOLATED">Isolated</option>
          </select>
        </label>

        {draft.neutralEarthingMode === "RESISTANCE_EARTHED" ? (
          <label>
            Neutral resistance (Ω)
            <input
              inputMode="decimal"
              name="neutralResistanceOhm"
              value={draft.neutralResistanceOhm}
              onChange={(event) =>
                updateField("neutralResistanceOhm", event.target.value)
              }
            />
          </label>
        ) : null}

        {draft.neutralEarthingMode === "REACTANCE_EARTHED" ? (
          <label>
            Neutral reactance (Ω)
            <input
              inputMode="decimal"
              name="neutralReactanceOhm"
              value={draft.neutralReactanceOhm}
              onChange={(event) =>
                updateField("neutralReactanceOhm", event.target.value)
              }
            />
          </label>
        ) : null}
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Source</legend>

        <label>
          Source code
          <input
            name="sourceCode"
            value={draft.sourceCode}
            onChange={(event) => updateField("sourceCode", event.target.value)}
          />
        </label>

        <label>
          Source name
          <input
            name="sourceName"
            value={draft.sourceName}
            onChange={(event) => updateField("sourceName", event.target.value)}
          />
        </label>

        <label>
          Source type
          <select
            name="sourceType"
            value={draft.sourceType}
            onChange={(event) => updateField("sourceType", event.target.value)}
          >
            <option value="">Select source type</option>
            <option value="UTILITY_GRID">Utility grid</option>
            <option value="SYNCHRONOUS_GENERATOR">Synchronous generator</option>
            <option value="ASYNCHRONOUS_MOTOR">Asynchronous motor</option>
            <option value="INVERTER_BASED_RESOURCE">Inverter-based resource</option>
            <option value="EQUIVALENT_SOURCE">Equivalent source</option>
          </select>
        </label>

        <label>
          Source representation
          <select
            name="sourceRepresentation"
            value={draft.sourceRepresentation}
            onChange={(event) =>
              updateField("sourceRepresentation", event.target.value)
            }
          >
            <option value="">Select representation</option>
            <option value="VOLTAGE_BEHIND_IMPEDANCE">
              Voltage behind impedance
            </option>
            <option value="CURRENT_INJECTION">Current injection</option>
          </select>
        </label>

        {usesImpedance ? (
          <>
            <label>
              Positive-sequence resistance (Ω)
              <input
                inputMode="decimal"
                name="sourceResistanceOhm"
                value={draft.sourceResistanceOhm}
                onChange={(event) =>
                  updateField("sourceResistanceOhm", event.target.value)
                }
              />
            </label>

            <label>
              Positive-sequence reactance (Ω)
              <input
                inputMode="decimal"
                name="sourceReactanceOhm"
                value={draft.sourceReactanceOhm}
                onChange={(event) =>
                  updateField("sourceReactanceOhm", event.target.value)
                }
              />
            </label>
          </>
        ) : null}

        {usesCurrentInjection ? (
          <label>
            Current contribution (kA)
            <input
              inputMode="decimal"
              name="currentContributionKa"
              value={draft.currentContributionKa}
              onChange={(event) =>
                updateField("currentContributionKa", event.target.value)
              }
            />
          </label>
        ) : null}
      </fieldset>

      {validationError ? <p role="alert">{validationError}</p> : null}

      <button disabled={disabled} type="submit">
        Calculate fault study
      </button>
    </form>
  );
}
