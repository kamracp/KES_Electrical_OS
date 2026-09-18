// Display rule A12 (Master Prompt v2.1 section 1A): summaries and tables show
// four significant figures with the unit; the exact engine decimal stays
// available for the tooltip, the persisted run and the JSON export.
//
// Rounding works on the decimal string itself (half-up on the digits). The
// value is never converted to a binary floating-point number, so the displayed
// figure cannot drift from the engine's Decimal result.

const PLAIN_DECIMAL = /^([+-]?)(\d+)(?:\.(\d+))?$/;

export const DISPLAY_SIGNIFICANT_FIGURES = 4;
export const EMPTY_QUANTITY = "—";

export type FormattedQuantity = {
  // Rounded value with its unit, for summaries and tables.
  display: string;
  // Exact engine value with its unit, for the tooltip; null when there is no value.
  exact: string | null;
};

function incrementDigits(digits: string): string {
  const chars = digits.split("");
  for (let index = chars.length - 1; index >= 0; index -= 1) {
    if (chars[index] !== "9") {
      chars[index] = String(Number(chars[index]) + 1);
      return chars.join("");
    }
    chars[index] = "0";
  }
  return `1${chars.join("")}`;
}

function stripLeadingZeros(digits: string): string {
  return digits.replace(/^0+(?=\d)/, "");
}

// Returns the value rounded half-up to the given significant figures, the
// value unchanged when it already has that many figures or fewer, or null when
// the text is not a plain decimal (for example exponent notation).
export function roundToSignificantFigures(
  value: string,
  figures: number = DISPLAY_SIGNIFICANT_FIGURES,
): string | null {
  const text = value.trim();
  const match = PLAIN_DECIMAL.exec(text);
  if (!match) {
    return null;
  }

  const sign = match[1] === "-" ? "-" : "";
  const integerPart = match[2] ?? "0";
  const fractionPart = match[3] ?? "";
  const digits = integerPart + fractionPart;
  const pointPosition = integerPart.length;

  const firstSignificant = digits.search(/[1-9]/);
  if (firstSignificant === -1) {
    return "0";
  }

  const keepEnd = firstSignificant + figures;
  if (keepEnd >= digits.length) {
    return text;
  }

  const kept = digits.slice(0, keepEnd);
  const roundUp = digits.charAt(keepEnd) >= "5";
  const rounded = roundUp ? incrementDigits(kept) : kept;
  const carried = rounded.replace(/^0+/, "").length > figures;

  if (keepEnd <= pointPosition) {
    const integer = rounded + "0".repeat(pointPosition - keepEnd);
    return `${sign}${stripLeadingZeros(integer)}`;
  }

  const fractionLength = keepEnd - pointPosition;
  const integer = stripLeadingZeros(rounded.slice(0, rounded.length - fractionLength)) || "0";
  const fullFraction = rounded.slice(rounded.length - fractionLength);
  // A carry (9.9996 -> 10.00) adds an integer digit; drop one fraction digit
  // so the figure count stays the same.
  const fraction = carried ? fullFraction.slice(0, -1) : fullFraction;

  return fraction ? `${sign}${integer}.${fraction}` : `${sign}${integer}`;
}

function withUnit(text: string, unit?: string): string {
  return unit ? `${text} ${unit}` : text;
}

export function formatQuantity(value: string | null | undefined, unit?: string): FormattedQuantity {
  if (value === null || value === undefined || value.trim() === "") {
    return { display: EMPTY_QUANTITY, exact: null };
  }

  const exact = withUnit(value.trim(), unit);
  const rounded = roundToSignificantFigures(value);

  // Not a plain decimal: show exactly what the engine sent rather than guess.
  return { display: rounded === null ? exact : withUnit(rounded, unit), exact };
}
