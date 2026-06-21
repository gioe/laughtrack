export const CLUB_TYPE_OPTIONS = [
    "club",
    "venue",
    "festival",
    "producer",
    "secret_location",
    "non_comedy",
] as const;

export type ClubType = (typeof CLUB_TYPE_OPTIONS)[number];

export const CLUB_TYPE_DEFINITIONS: Record<ClubType, string> = {
    club: "Comedy-first fixed venue that should appear as a normal public club.",
    venue: "Mixed-purpose physical venue that legitimately hosts comedy programming.",
    festival:
        "Recurring comedy festival; scraper scheduling may treat it seasonally.",
    producer: "Producer or organizer identity, not a public physical venue.",
    secret_location:
        "Placeholder for shows whose venue is intentionally undisclosed.",
    non_comedy: "Hidden discovery placeholder for a reviewed non-comedy venue.",
};
