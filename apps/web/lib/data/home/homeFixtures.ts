import { ShowDTO } from "@/objects/class/show/show.interface";

// Deterministic fixture shows used by Playwright visual regression tests when
// E2E_FIXTURE_MODE=1 is set. The UTC instant and timezone together fully
// determine the rendered wallclock, so screenshots stay pixel-stable across
// runs. The date sits outside DST observance in every US zone to avoid
// EST/EDT label drift.
const FIXTURE_DATE = new Date("2026-02-14T01:00:00Z");

const PLACEHOLDER_IMAGE = "/placeholders/club-placeholder.svg";

function buildFixtureShow(
    id: number,
    clubName: string,
    timezone: string,
    name: string,
    lineup: string[],
    address: string,
): ShowDTO {
    return {
        id,
        clubName,
        date: FIXTURE_DATE,
        name,
        address,
        imageUrl: PLACEHOLDER_IMAGE,
        tickets: [
            {
                price: 25,
                soldOut: false,
                purchaseUrl: "https://example.com/tickets",
                type: "general",
            },
        ],
        lineup: lineup.map((n, i) => ({
            id: id * 100 + i,
            uuid: `fixture-comedian-${id}-${i}`,
            name: n,
            imageUrl: PLACEHOLDER_IMAGE,
            hasImage: false,
        })),
        soldOut: false,
        room: null,
        timezone,
    };
}

export const FIXTURE_SHOWS_TONIGHT: ShowDTO[] = [
    buildFixtureShow(
        9001,
        "Gotham Comedy Club",
        "America/New_York",
        "Headliners Night",
        ["Jane Doe", "John Smith"],
        "208 W 23rd St, New York, NY",
    ),
    buildFixtureShow(
        9002,
        "Laugh Factory Chicago",
        "America/Chicago",
        "Late Show",
        ["Alex Comic", "Pat Funny"],
        "3175 N Broadway, Chicago, IL",
    ),
];

export const FIXTURE_SHOWS_TRENDING: ShowDTO[] = [
    buildFixtureShow(
        9101,
        "Comedy Cellar",
        "America/New_York",
        "Weekend Showcase",
        ["Riley East", "Morgan Coast"],
        "117 MacDougal St, New York, NY",
    ),
    buildFixtureShow(
        9102,
        "The Second City",
        "America/Chicago",
        "Mainstage",
        ["Casey Central", "Taylor Heartland"],
        "1616 N Wells St, Chicago, IL",
    ),
    buildFixtureShow(
        9103,
        "Comedy Works Denver",
        "America/Denver",
        "Mile High Laughs",
        ["Jordan Peak", "Sky Summit"],
        "1226 15th St, Denver, CO",
    ),
    buildFixtureShow(
        9104,
        "The Comedy Store",
        "America/Los_Angeles",
        "Main Room",
        ["Avery West", "Quinn Pacific"],
        "8433 Sunset Blvd, West Hollywood, CA",
    ),
];
