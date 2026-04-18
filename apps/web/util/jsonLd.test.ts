import { describe, it, expect } from "vitest";
import { buildClubJsonLd, buildOpeningHoursSpecification } from "./jsonLd";
import { ClubDTO } from "@/objects/class/club/club.interface";

function baseClub(overrides: Partial<ClubDTO> = {}): ClubDTO {
    return {
        id: 1,
        name: "Test Club",
        imageUrl: "https://cdn.example.com/club.jpg",
        website: "https://testclub.example.com",
        address: "123 Main St, New York, NY 10001",
        city: "New York",
        state: "NY",
        zipCode: "10001",
        ...overrides,
    };
}

describe("buildOpeningHoursSpecification", () => {
    it("returns undefined for empty hours object", () => {
        expect(buildOpeningHoursSpecification({})).toBeUndefined();
    });

    it("returns undefined for null/undefined/non-object input", () => {
        expect(buildOpeningHoursSpecification(null)).toBeUndefined();
        expect(buildOpeningHoursSpecification(undefined)).toBeUndefined();
        expect(buildOpeningHoursSpecification("9-5")).toBeUndefined();
        expect(buildOpeningHoursSpecification(["9-5"])).toBeUndefined();
    });

    it("maps all 7 days to OpeningHoursSpecification entries with 24-hour opens/closes", () => {
        const hours = {
            monday: "9:00 AM - 5:00 PM",
            tuesday: "9:00 AM - 5:00 PM",
            wednesday: "9:00 AM - 5:00 PM",
            thursday: "9:00 AM - 5:00 PM",
            friday: "9:00 AM - 11:00 PM",
            saturday: "12:00 PM - 11:30 PM",
            sunday: "12:00 PM - 8:00 PM",
        };
        const result = buildOpeningHoursSpecification(hours);
        expect(result).toEqual([
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Monday",
                opens: "09:00",
                closes: "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Tuesday",
                opens: "09:00",
                closes: "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Wednesday",
                opens: "09:00",
                closes: "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Thursday",
                opens: "09:00",
                closes: "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Friday",
                opens: "09:00",
                closes: "23:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Saturday",
                opens: "12:00",
                closes: "23:30",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Sunday",
                opens: "12:00",
                closes: "20:00",
            },
        ]);
    });

    it("skips unknown day keys", () => {
        const hours = {
            funday: "9:00 AM - 5:00 PM",
            monday: "9:00 AM - 5:00 PM",
        };
        const result = buildOpeningHoursSpecification(hours) as Array<{
            dayOfWeek: string;
        }>;
        expect(result).toHaveLength(1);
        expect(result[0].dayOfWeek).toBe("Monday");
    });

    it("skips unparseable hours strings (e.g. 'Closed')", () => {
        const hours = {
            monday: "Closed",
            tuesday: "9:00 AM - 5:00 PM",
        };
        const result = buildOpeningHoursSpecification(hours) as Array<{
            dayOfWeek: string;
        }>;
        expect(result).toHaveLength(1);
        expect(result[0].dayOfWeek).toBe("Tuesday");
    });

    it("returns undefined when every entry is skipped", () => {
        const hours = { monday: "Closed", tuesday: "by appointment" };
        expect(buildOpeningHoursSpecification(hours)).toBeUndefined();
    });

    it("handles 12 AM / 12 PM boundary correctly", () => {
        const result = buildOpeningHoursSpecification({
            monday: "12:00 AM - 12:00 PM",
        }) as Array<{ opens: string; closes: string }>;
        expect(result[0].opens).toBe("00:00");
        expect(result[0].closes).toBe("12:00");
    });

    it("accepts shorthand without minutes ('9 AM - 5 PM')", () => {
        const result = buildOpeningHoursSpecification({
            monday: "9 AM - 5 PM",
        }) as Array<{ opens: string; closes: string }>;
        expect(result[0].opens).toBe("09:00");
        expect(result[0].closes).toBe("17:00");
    });

    it("accepts case-insensitive day keys and meridiems", () => {
        const result = buildOpeningHoursSpecification({
            MONDAY: "9:00 am - 5:00 pm",
        }) as Array<{ dayOfWeek: string; opens: string; closes: string }>;
        expect(result[0].dayOfWeek).toBe("Monday");
        expect(result[0].opens).toBe("09:00");
        expect(result[0].closes).toBe("17:00");
    });
});

describe("buildClubJsonLd", () => {
    it("does not emit description or openingHoursSpecification when fields are absent", () => {
        const jsonLd = buildClubJsonLd(baseClub()) as Record<string, unknown>;
        expect(jsonLd.description).toBeUndefined();
        expect(jsonLd.openingHoursSpecification).toBeUndefined();
    });

    it("emits description when Club.description is non-empty", () => {
        const jsonLd = buildClubJsonLd(
            baseClub({ description: "The best comedy club in town." }),
        ) as Record<string, unknown>;
        expect(jsonLd.description).toBe("The best comedy club in town.");
    });

    it("omits description when Club.description is empty or whitespace", () => {
        const empty = buildClubJsonLd(baseClub({ description: "" })) as Record<
            string,
            unknown
        >;
        expect(empty.description).toBeUndefined();
        const blank = buildClubJsonLd(
            baseClub({ description: "   " }),
        ) as Record<string, unknown>;
        expect(blank.description).toBeUndefined();
    });

    it("emits openingHoursSpecification when hours is a populated map", () => {
        const jsonLd = buildClubJsonLd(
            baseClub({
                hours: {
                    monday: "9:00 AM - 5:00 PM",
                    tuesday: "9:00 AM - 5:00 PM",
                },
            }),
        ) as Record<string, unknown>;
        expect(jsonLd.openingHoursSpecification).toEqual([
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Monday",
                opens: "09:00",
                closes: "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                dayOfWeek: "Tuesday",
                opens: "09:00",
                closes: "17:00",
            },
        ]);
    });
});
