// Single source of truth for the 15 product modules (EOS-01..15).
// Home page and sidebar navigation both render from this list, so no module
// can silently disappear from the product. Status mirrors docs/project-status.md.

export type ModuleStatus = "LIVE" | "BACKEND_ONLY" | "PLANNED";

export type ModuleDefinition = {
  code: string;
  name: string;
  summary: string;
  status: ModuleStatus;
  // A route exists only when the page works; PLANNED and BACKEND_ONLY have none.
  route: string | null;
};

export const MODULE_STATUS_LABELS: Record<ModuleStatus, string> = {
  LIVE: "Live",
  BACKEND_ONLY: "Backend only",
  PLANNED: "Planned",
};

export const MODULES: readonly ModuleDefinition[] = [
  {
    code: "EOS-01",
    name: "Project configuration",
    summary: "Project identity, jurisdiction profile, units and applicable standards.",
    status: "BACKEND_ONLY",
    route: null,
  },
  {
    code: "EOS-02",
    name: "Load and demand",
    summary: "Connected load, diversity and maximum demand estimation.",
    status: "BACKEND_ONLY",
    route: null,
  },
  {
    code: "EOS-03",
    name: "Transformer, DG, UPS and PV",
    summary: "Source sizing for transformers, generators, UPS and PV systems.",
    status: "BACKEND_ONLY",
    route: null,
  },
  {
    code: "EOS-04",
    name: "Short-circuit study",
    summary: "Fault currents at a bus with sequence impedances and source contributions.",
    status: "LIVE",
    route: "/fault-study",
  },
  {
    code: "EOS-05",
    name: "Protection coordination",
    summary: "Relay and device settings, discrimination and coordination checks.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-06",
    name: "Cable sizing",
    summary: "LV cable selection with ampacity, voltage-drop and short-circuit checks.",
    status: "LIVE",
    route: "/cable-sizing",
  },
  {
    code: "EOS-07",
    name: "Panels and switchboards",
    summary: "Assembly checks against IEC 61439 ratings and construction rules.",
    status: "BACKEND_ONLY",
    route: null,
  },
  {
    code: "EOS-08",
    name: "Earthing",
    summary: "Earth grid, electrode and conductor sizing with touch and step checks.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-09",
    name: "Lightning protection",
    summary: "Risk assessment and air-termination layout by the rolling-sphere method.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-10",
    name: "Surge protection",
    summary: "SPD type, location and rating selection.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-11",
    name: "Power factor and harmonics",
    summary: "Compensation sizing and harmonic distortion checks.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-12",
    name: "Cable tray and routing",
    summary: "Tray fill, support spacing and route loading.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-13",
    name: "Deliverables",
    summary: "Calculation reports, schedules and drawings issued from approved runs.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-14",
    name: "FAT and SAT",
    summary: "Factory and site acceptance test calculators and records.",
    status: "PLANNED",
    route: null,
  },
  {
    code: "EOS-15",
    name: "Metering, BMS and SCADA",
    summary: "Metering points, signal lists and supervisory interfaces.",
    status: "PLANNED",
    route: null,
  },
];

export function getModule(code: string): ModuleDefinition | undefined {
  return MODULES.find((module) => module.code === code);
}

export function liveModules(): ModuleDefinition[] {
  return MODULES.filter((module) => module.status === "LIVE");
}
