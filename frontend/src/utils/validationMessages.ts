// Readable form validation messages (project-status follow-up, EOS-04 c1).
// A schema issue carries a raw path such as ["sources", 0, "name"]; the forms
// showed it verbatim ("sources.0.name: Too small: ..."). This helper turns the
// path into the label the user sees on the form and the issue into a sentence
// built from the issue's structured fields, not from its wording.

export interface ValidationIssueLike {
  path: ReadonlyArray<PropertyKey>;
  message: string;
  code?: string;
  // zod 4 names the checked kind "origin"; zod 3 named it "type".
  origin?: string;
  type?: string;
  minimum?: number | bigint;
  maximum?: number | bigint;
  inclusive?: boolean;
  expected?: string;
  received?: string;
}

export interface ValidationLabels {
  // Keyed by the path with list indexes replaced by "*", e.g. "sources.*.name".
  fields: Readonly<Record<string, string>>;
  // Singular name of a list, keyed by the list segment, e.g. sources -> "Source".
  groups?: Readonly<Record<string, string>>;
}

const NO_LABELS: ValidationLabels = { fields: {} };

function humanize(segment: string): string {
  const words = segment.split("_").join(" ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : segment;
}

function singular(segment: string): string {
  if (/(ses|ches|xes)$/.test(segment)) {
    return segment.slice(0, -2);
  }
  return segment.endsWith("s") ? segment.slice(0, -1) : segment;
}

// ["sources", 0, "name"] -> "Source 1 — Name"; list items are numbered from one.
export function describeLocation(
  path: ReadonlyArray<PropertyKey>,
  labels: ValidationLabels = NO_LABELS,
): string {
  const segments = path.map((segment) => (typeof segment === "number" ? segment : String(segment)));
  if (segments.length === 0) {
    return "";
  }

  const pattern = segments.map((segment) => (typeof segment === "number" ? "*" : segment)).join(".");

  const parts: string[] = [];
  segments.forEach((segment, index) => {
    if (typeof segment !== "number") {
      return;
    }
    const list = segments[index - 1];
    const name =
      typeof list === "string" ? (labels.groups?.[list] ?? humanize(singular(list))) : "Item";
    parts.push(`${name} ${segment + 1}`);
  });

  const last = segments[segments.length - 1];
  const fieldLabel = labels.fields[pattern] ?? (typeof last === "string" ? humanize(last) : "");
  if (fieldLabel) {
    parts.push(fieldLabel);
  }

  return parts.join(" — ");
}

function entries(count: string): string {
  return count === "1" ? "entry" : "entries";
}

// The sentence that follows the label, or null when the issue kind is not known.
function describeProblem(issue: ValidationIssueLike): string | null {
  const kind = issue.origin ?? issue.type;
  const isList = kind === "array" || kind === "set";

  if (issue.code === "too_small" && issue.minimum !== undefined) {
    const minimum = String(issue.minimum);
    if (kind === "string") {
      return minimum === "1" ? "is required." : `must have at least ${minimum} characters.`;
    }
    if (isList) {
      return `needs at least ${minimum} ${entries(minimum)}.`;
    }
    return issue.inclusive === false
      ? `must be greater than ${minimum}.`
      : `must be at least ${minimum}.`;
  }

  if (issue.code === "too_big" && issue.maximum !== undefined) {
    const maximum = String(issue.maximum);
    if (kind === "string") {
      return `must have at most ${maximum} characters.`;
    }
    if (isList) {
      return `allows at most ${maximum} ${entries(maximum)}.`;
    }
    return issue.inclusive === false
      ? `must be less than ${maximum}.`
      : `must be at most ${maximum}.`;
  }

  if (issue.code === "invalid_type") {
    if (issue.received === "undefined" || /received undefined$/.test(issue.message)) {
      return "is required.";
    }
    return issue.expected === "number" ? "must be a number." : "has an invalid value.";
  }

  if (issue.code === "invalid_value" || issue.code === "invalid_enum_value") {
    return "must be one of the listed options.";
  }

  return null;
}

// "Source 1 — Name is required." Unknown issue kinds keep their own message
// after the label, so no information is lost.
export function describeValidationIssue(
  issue: ValidationIssueLike,
  labels: ValidationLabels = NO_LABELS,
): string {
  const location = describeLocation(issue.path, labels);
  if (!location) {
    return issue.message;
  }

  const problem = describeProblem(issue);
  return problem ? `${location} ${problem}` : `${location}: ${issue.message}`;
}
