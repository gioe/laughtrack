import { beforeEach, describe, expect, it, vi } from "vitest";
const { mockClubs } = vi.hoisted(() => ({ mockClubs: vi.fn() }));
vi.mock("@/lib/db", () => ({ db: { club: { groupBy: mockClubs } } }));
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildShowDateClause, showDateTimezone } from "./showDateBasis";

function helper(day = "2030-08-18", dateBasis: "venue" | "request" = "venue") {
    return new QueryHelper({
        params: { fromDate: day, toDate: day, dateBasis },
        timezone: "America/New_York",
    });
}
beforeEach(() => {
    vi.clearAllMocks();
    mockClubs.mockResolvedValue([
        { timezone: "America/New_York" },
        { timezone: "America/Los_Angeles" },
    ]);
});

describe("venue calendar date filtering", () => {
    it("keeps the late-night destination show and excludes its adjacent civil day", async () => {
        const where = await buildShowDateClause(helper(), { visible: true });
        expect(where).toEqual({
            OR: [
                {
                    club: { timezone: "America/New_York" },
                    date: {
                        gte: "2030-08-18T04:00:00.000Z",
                        lt: "2030-08-19T04:00:00.000Z",
                    },
                },
                {
                    club: { timezone: "America/Los_Angeles" },
                    date: {
                        gte: "2030-08-18T07:00:00.000Z",
                        lt: "2030-08-19T07:00:00.000Z",
                    },
                },
            ],
        });
        const branches = where.OR as {
            club: { timezone: string };
            date: { gte: string; lt: string };
        }[];
        const pacific = branches[1].date;
        expect(
            "2030-08-19T06:30:00.000Z" >= pacific.gte &&
                "2030-08-19T06:30:00.000Z" < pacific.lt,
        ).toBe(true);
        expect("2030-08-18T06:30:00.000Z" >= pacific.gte).toBe(false);
        const included = (instant: string) =>
            instant >= pacific.gte && instant < pacific.lt;
        expect(included("2030-08-18T06:59:59.999Z")).toBe(false);
        expect(included("2030-08-18T07:00:00.000Z")).toBe(true);
        expect(included("2030-08-19T06:59:59.999Z")).toBe(true);
        // Keep microseconds as ISO text: JS Date would truncate .999500 to .999.
        // UTC ISO ordering across these seconds matches timestamptz ordering.
        expect(included("2030-08-19T06:59:59.999500Z")).toBe(true);
        expect(included("2030-08-19T07:00:00.000Z")).toBe(false);
        expect(included("2030-08-19T07:00:00.001Z")).toBe(false);
        expect(mockClubs).toHaveBeenCalledWith({
            where: { visible: true },
            by: ["timezone"],
        });
    });
    it.each([
        ["2030-03-10", "2030-03-10T05:00:00.000Z", "2030-03-11T04:00:00.000Z"],
        ["2030-11-03", "2030-11-03T04:00:00.000Z", "2030-11-04T05:00:00.000Z"],
    ])("respects the DST civil-day bounds for %s", async (day, gte, lt) => {
        mockClubs.mockResolvedValue([{ timezone: "America/New_York" }]);
        expect(await buildShowDateClause(helper(day), {})).toEqual({
            OR: [{ club: { timezone: "America/New_York" }, date: { gte, lt } }],
        });
    });
    it("uses request timezone for missing and invalid venue zones without widening their club match", async () => {
        mockClubs.mockResolvedValue([
            { timezone: null },
            { timezone: "Not/AZone" },
        ]);
        const date = {
            gte: "2030-08-18T04:00:00.000Z",
            lt: "2030-08-19T04:00:00.000Z",
        };
        expect(await buildShowDateClause(helper(), {})).toEqual({
            OR: [
                { club: { timezone: null }, date },
                { club: { timezone: "Not/AZone" }, date },
            ],
        });
        expect(showDateTimezone(null, "America/New_York")).toBe(
            "America/New_York",
        );
        expect(showDateTimezone("Not/AZone", "America/New_York")).toBe(
            "America/New_York",
        );
    });
    it("keeps request-basis callers and unfiltered upcoming searches unchanged without a metadata query", async () => {
        const legacy = helper("2030-08-18", "request");
        expect(await buildShowDateClause(legacy, {})).toEqual(
            legacy.getDateClause(),
        );
        const unfiltered = new QueryHelper({
            params: { dateBasis: "venue" },
            timezone: "America/New_York",
        });
        expect(await buildShowDateClause(unfiltered, {})).toEqual({});
        expect(mockClubs).not.toHaveBeenCalled();
    });
    it("matches no shows when no candidate clubs remain", async () => {
        mockClubs.mockResolvedValue([]);
        expect(await buildShowDateClause(helper(), {})).toEqual({ OR: [] });
    });
});
