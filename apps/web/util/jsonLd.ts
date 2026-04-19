import { ClubDTO } from "@/objects/class/club/club.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";

const BASE_URL =
    process.env.NEXT_PUBLIC_WEBSITE_URL ?? "https://www.laugh-track.com";

function ensureAbsoluteUrl(url: string | undefined | null): string | undefined {
    if (!url) return undefined;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("/")) return `${BASE_URL}${url}`;
    return `https://${url}`;
}

export function buildClubJsonLd(club: ClubDTO): object {
    const jsonLd: Record<string, unknown> = {
        "@context": "https://schema.org",
        "@type": "EntertainmentBusiness",
        name: club.name,
        url: club.website,
        image: ensureAbsoluteUrl(club.imageUrl),
    };

    if (club.address) {
        const parts = parseAddress(club.address);
        jsonLd.address = {
            "@type": "PostalAddress",
            streetAddress: parts.street,
            addressLocality: club.city ?? parts.city,
            addressRegion: club.state ?? parts.state,
            postalCode: club.zipCode ?? parts.zip,
            addressCountry: "US",
        };
    }

    if (club.phone_number) {
        jsonLd.telephone = club.phone_number;
    }

    if (
        typeof club.description === "string" &&
        club.description.trim() !== ""
    ) {
        jsonLd.description = club.description;
    }

    const openingHours = buildOpeningHoursSpecification(club.hours);
    if (openingHours) {
        jsonLd.openingHoursSpecification = openingHours;
    }

    return jsonLd;
}

const DAY_OF_WEEK: Record<string, string> = {
    monday: "Monday",
    tuesday: "Tuesday",
    wednesday: "Wednesday",
    thursday: "Thursday",
    friday: "Friday",
    saturday: "Saturday",
    sunday: "Sunday",
};

function to24Hour(h: number, m: number, meridiem: string): string | null {
    if (h < 1 || h > 12 || m < 0 || m > 59) return null;
    const mer = meridiem.toLowerCase();
    let hh = h;
    if (mer === "am") {
        if (h === 12) hh = 0;
    } else if (mer === "pm") {
        if (h !== 12) hh = h + 12;
    } else {
        return null;
    }
    return `${String(hh).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function parseHoursRange(
    raw: string,
): { opens: string; closes: string } | null {
    const match = raw
        .trim()
        .match(
            /^(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)\s*[-–—]\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)$/,
        );
    if (!match) return null;
    const [, h1, m1 = "00", mer1, h2, m2 = "00", mer2] = match;
    const opens = to24Hour(parseInt(h1, 10), parseInt(m1, 10), mer1);
    const closes = to24Hour(parseInt(h2, 10), parseInt(m2, 10), mer2);
    if (!opens || !closes) return null;
    return { opens, closes };
}

// Multi-shift hours (e.g. "11am-2pm, 5pm-10pm" for venues with separate
// lunch + dinner service) are emitted by the Places enrichment step as a
// single comma-joined string per day. Splitting here lets each sub-range
// surface as its own OpeningHoursSpecification so SEO output stays
// consistent with the scraper's new format.
function parseHoursRanges(raw: string): { opens: string; closes: string }[] {
    return raw
        .split(",")
        .map((segment) => parseHoursRange(segment))
        .filter(
            (parsed): parsed is { opens: string; closes: string } =>
                parsed !== null,
        );
}

export function buildOpeningHoursSpecification(
    hours: unknown,
): object[] | undefined {
    if (!hours || typeof hours !== "object" || Array.isArray(hours)) {
        return undefined;
    }
    const entries: object[] = [];
    for (const [day, value] of Object.entries(
        hours as Record<string, unknown>,
    )) {
        if (typeof value !== "string" || value.trim() === "") continue;
        const canonicalDay = DAY_OF_WEEK[day.toLowerCase()];
        if (!canonicalDay) continue;
        for (const parsed of parseHoursRanges(value)) {
            entries.push({
                "@type": "OpeningHoursSpecification",
                dayOfWeek: canonicalDay,
                opens: parsed.opens,
                closes: parsed.closes,
            });
        }
    }
    return entries.length > 0 ? entries : undefined;
}

export function buildComedianJsonLd(comedian: ComedianDTO): object {
    const sameAs: string[] = [];
    const social = comedian.social_data;
    if (social?.instagram_account) {
        sameAs.push(`https://www.instagram.com/${social.instagram_account}`);
    }
    if (social?.tiktok_account) {
        sameAs.push(`https://www.tiktok.com/@${social.tiktok_account}`);
    }
    if (social?.youtube_account) {
        sameAs.push(`https://www.youtube.com/@${social.youtube_account}`);
    }
    if (social?.website) {
        sameAs.push(ensureAbsoluteUrl(social.website)!);
    }
    if (social?.linktree) {
        sameAs.push(ensureAbsoluteUrl(social.linktree)!);
    }

    const jsonLd: Record<string, unknown> = {
        "@context": "https://schema.org",
        "@type": "Person",
        name: comedian.name,
        image: ensureAbsoluteUrl(comedian.imageUrl),
        url: `${BASE_URL}/comedian/${encodeURIComponent(comedian.name)}`,
    };

    if (sameAs.length > 0) {
        jsonLd.sameAs = sameAs;
    }

    return jsonLd;
}

export function buildShowJsonLd(show: ShowDTO): object {
    const jsonLd: Record<string, unknown> = {
        "@context": "https://schema.org",
        "@type": "Event",
        name: show.name ?? `Comedy Show at ${show.clubName}`,
        startDate: new Date(show.date).toISOString(),
        eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        eventStatus: "https://schema.org/EventScheduled",
        image: ensureAbsoluteUrl(show.imageUrl),
    };

    if (show.description) {
        jsonLd.description = show.description;
    }

    if (show.clubName) {
        jsonLd.location = {
            "@type": "Place",
            name: show.clubName,
            ...(show.address && {
                address: {
                    "@type": "PostalAddress",
                    streetAddress: show.address,
                },
            }),
        };
    }

    if (show.lineup && show.lineup.length > 0) {
        jsonLd.performer = show.lineup.map((c) => ({
            "@type": "Person",
            name: c.name,
            image: ensureAbsoluteUrl(c.imageUrl),
        }));
    }

    const tickets = show.tickets?.filter((t) => t.purchaseUrl) ?? [];
    if (tickets.length > 0) {
        jsonLd.offers = tickets.map((t) => {
            const offer: Record<string, unknown> = {
                "@type": "Offer",
                url: t.purchaseUrl,
                availability: t.soldOut
                    ? "https://schema.org/SoldOut"
                    : "https://schema.org/InStock",
            };
            if (t.price != null && t.price > 0) {
                offer.price = String(t.price);
                offer.priceCurrency = "USD";
            }
            return offer;
        });
    }

    return jsonLd;
}

export function buildWebSiteJsonLd(): object {
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: "LaughTrack",
        url: BASE_URL,
        potentialAction: {
            "@type": "SearchAction",
            target: {
                "@type": "EntryPoint",
                urlTemplate: `${BASE_URL}/show/search?q={search_term_string}`,
            },
            "query-input": "required name=search_term_string",
        },
    };
}

function parseAddress(address: string): {
    street: string;
    city: string;
    state: string;
    zip: string;
} {
    // Typical format: "123 Main St, City, ST 12345"
    const parts = address.split(",").map((s) => s.trim());
    const street = parts[0] ?? address;
    const city = parts[1] ?? "";
    const stateZip = parts[2] ?? "";
    const stateZipMatch = stateZip.match(/^([A-Z]{2})\s*(\d{5})?/);
    return {
        street,
        city,
        state: stateZipMatch?.[1] ?? "",
        zip: stateZipMatch?.[2] ?? "",
    };
}
