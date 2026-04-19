import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockCount, mockFindMany } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { count: mockCount, findMany: mockFindMany } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn(() => []),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets: any[]) => tickets),
}));

import { findPastShowsForComedian } from "./findPastShowsForComedian";

function makeHelper(
    overrides: Partial<{
        comedian: string | undefined;
        userId: string | undefined;
    }> = {},
) {
    const comedian =
        "comedian" in overrides ? overrides.comedian : "some-comedian-uuid";
    return {
        params: { comedian },
        getLineupItemClause: vi.fn(() => ({ lineupItems: {} })),
        getUserId: vi.fn(() => overrides.userId ?? undefined),
    };
}

function makeShow(
    overrides: Partial<{
        id: number;
        name: string;
        date: Date;
        description: string | null;
        popularity: number;
        room: string | null;
        tickets: any[];
        club: {
            name: string;
            address: string;
            zipCode?: string | null;
            hasImage?: boolean;
            timezone?: string | null;
        };
        lineupItems: any[];
    }> = {},
) {
    return {
        id: 1,
        name: "Past Show",
        date: new Date("2025-01-01"),
        description: null,
        popularity: 5,
        room: null,
        tickets: [],
        club: {
            name: "Test Club",
            address: "123 Main St",
            zipCode: "10001",
            hasImage: true,
            timezone: "America/New_York",
        },
        lineupItems: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindMany.mockResolvedValue([]);
    mockCount.mockResolvedValue(0);
});

describe("findPastShowsForComedian", () => {
    describe("short-circuit when comedian missing", () => {
        it("returns empty result without hitting the database when comedian is missing", async () => {
            const helper = makeHelper({ comedian: undefined });

            const result = await findPastShowsForComedian(helper as any);

            expect(result).toEqual({ shows: [], totalCount: 0 });
            expect(mockCount).not.toHaveBeenCalled();
            expect(mockFindMany).not.toHaveBeenCalled();
        });
    });

    describe("happy path", () => {
        it("returns totalCount and mapped shows", async () => {
            const show = makeShow({ id: 42, name: "Old Show" });
            mockCount.mockResolvedValue(3);
            mockFindMany.mockResolvedValue([show]);

            const result = await findPastShowsForComedian(makeHelper() as any);

            expect(result.totalCount).toBe(3);
            expect(result.shows).toHaveLength(1);
            expect(result.shows[0].id).toBe(42);
            expect(result.shows[0].name).toBe("Old Show");
            expect(result.shows[0].distanceMiles).toBeNull();
        });
    });

    describe("timezone mapping", () => {
        it("selects club.timezone from the database", async () => {
            let capturedSelect: any;
            mockFindMany.mockImplementation((args: any) => {
                capturedSelect = args.select;
                return Promise.resolve([]);
            });

            await findPastShowsForComedian(makeHelper() as any);

            expect(capturedSelect.club.select.timezone).toBe(true);
        });

        it("maps a Los Angeles club.timezone onto the returned DTO", async () => {
            const show = makeShow({
                club: {
                    name: "Laugh Factory",
                    address: "8001 Sunset Blvd",
                    zipCode: "90046",
                    hasImage: true,
                    timezone: "America/Los_Angeles",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findPastShowsForComedian(makeHelper() as any);

            expect(result.shows[0].timezone).toBe("America/Los_Angeles");
        });

        it("maps a Chicago club.timezone onto the returned DTO", async () => {
            const show = makeShow({
                club: {
                    name: "Zanies",
                    address: "1548 N Wells St",
                    zipCode: "60610",
                    hasImage: true,
                    timezone: "America/Chicago",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findPastShowsForComedian(makeHelper() as any);

            expect(result.shows[0].timezone).toBe("America/Chicago");
        });
    });

    describe("pagination", () => {
        it("defaults to skip=0, take=20 when no options are passed", async () => {
            let capturedArgs: any;
            mockFindMany.mockImplementation((args: any) => {
                capturedArgs = args;
                return Promise.resolve([]);
            });

            await findPastShowsForComedian(makeHelper() as any);

            expect(capturedArgs.skip).toBe(0);
            expect(capturedArgs.take).toBe(20);
        });

        it("applies skip = page * size for subsequent pages", async () => {
            let capturedArgs: any;
            mockFindMany.mockImplementation((args: any) => {
                capturedArgs = args;
                return Promise.resolve([]);
            });

            await findPastShowsForComedian(makeHelper() as any, {
                page: 2,
                size: 20,
            });

            expect(capturedArgs.skip).toBe(40);
            expect(capturedArgs.take).toBe(20);
        });

        it("coerces negative page to 0 and undersized size to 1", async () => {
            let capturedArgs: any;
            mockFindMany.mockImplementation((args: any) => {
                capturedArgs = args;
                return Promise.resolve([]);
            });

            await findPastShowsForComedian(makeHelper() as any, {
                page: -5,
                size: 0,
            });

            expect(capturedArgs.skip).toBe(0);
            expect(capturedArgs.take).toBe(1);
        });
    });

    describe("null timezone edge case", () => {
        it("returns null timezone when the club has no timezone configured", async () => {
            const show = makeShow({
                club: {
                    name: "Unknown Venue",
                    address: "000 Nowhere",
                    zipCode: null,
                    hasImage: false,
                    timezone: null,
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findPastShowsForComedian(makeHelper() as any);

            expect(result.shows[0].timezone).toBeNull();
        });
    });
});
