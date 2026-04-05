import { ClubDTO } from "@/objects/class/club/club.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";

const BASE_URL =
    process.env.NEXT_PUBLIC_WEBSITE_URL ?? "https://www.laugh-track.com";

export function buildClubJsonLd(club: ClubDTO): object {
    const jsonLd: Record<string, unknown> = {
        "@context": "https://schema.org",
        "@type": "EntertainmentBusiness",
        name: club.name,
        url: club.website,
        image: club.imageUrl,
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

    return jsonLd;
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
        sameAs.push(social.website);
    }
    if (social?.linktree) {
        sameAs.push(social.linktree);
    }

    const jsonLd: Record<string, unknown> = {
        "@context": "https://schema.org",
        "@type": "Person",
        name: comedian.name,
        image: comedian.imageUrl,
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
        image: show.imageUrl,
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
            image: c.imageUrl,
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
