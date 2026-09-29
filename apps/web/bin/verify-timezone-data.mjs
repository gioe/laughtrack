import { pathToFileURL } from "node:url";

// Behavioral checks are authoritative: Node major versions alone do not pin ICU.
// Alberta: IANA 2026c; British Columbia: IANA 2026b.
export const timezoneCases = [
  ["2026-01-15T20:00:00Z", "America/Edmonton", "13:00"],
  ["2026-01-15T20:00:00Z", "America/Vancouver", "12:00"],
  ["2026-10-31T20:00:00Z", "America/Edmonton", "14:00"],
  ["2026-10-31T20:00:00Z", "America/Vancouver", "13:00"],
  ["2026-11-01T07:59:00Z", "America/Edmonton", "01:59"],
  ["2026-11-01T08:00:00Z", "America/Edmonton", "02:00"],
  ["2026-11-01T08:59:00Z", "America/Vancouver", "01:59"],
  ["2026-11-01T09:00:00Z", "America/Vancouver", "02:00"],
  ["2026-12-01T20:00:00Z", "America/Edmonton", "14:00"],
  ["2026-12-01T20:00:00Z", "America/Vancouver", "13:00"],
  ["2027-03-01T20:00:00Z", "America/Edmonton", "14:00"],
  ["2027-03-01T20:00:00Z", "America/Vancouver", "13:00"],
  ["2026-12-01T20:00:00Z", "America/Denver", "13:00"],
  ["2026-12-01T20:00:00Z", "America/Los_Angeles", "12:00"],
];

export function verifyTimezoneData() {
  for (const [instant, timeZone, expected] of timezoneCases) {
    const actual = new Intl.DateTimeFormat("en-GB", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(new Date(instant));
    if (actual !== expected) {
      throw new Error(
        `Stale Node timezone data: ${timeZone} at ${instant}: expected ${expected}, got ${actual}; Node=${process.versions.node}, ICU=${process.versions.icu}, tz=${process.versions.tz}. Use the supported Node 24 runtime with IANA 2026c or newer.`,
      );
    }
  }
  return {
    node: process.versions.node,
    icu: process.versions.icu,
    tz: process.versions.tz,
    cases: timezoneCases.length,
  };
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  console.log(JSON.stringify(verifyTimezoneData()));
}
