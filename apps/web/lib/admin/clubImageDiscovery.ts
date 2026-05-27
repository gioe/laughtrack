import net from "node:net";
import sharp from "sharp";

export type ClubImageDiscoveryInput = {
    clubName: string;
    website: string | null;
    websiteScrapingUrl: string | null;
};

export type ClubImageCandidate = {
    imageUrl: string;
    sourcePage: string;
    width: number | null;
    height: number | null;
    mimeType: string | null;
    score: number;
    reasons: string[];
};

export type ClubImageDiscoveryResult = {
    seedPages: string[];
    crawledPages: string[];
    candidates: ClubImageCandidate[];
};

type InspectedImage = {
    url: string;
    width: number | null;
    height: number | null;
    mimeType: string | null;
};

type DiscoveryOptions = {
    fetch?: typeof fetch;
    inspectImage?: (url: string) => Promise<InspectedImage | null>;
    maxPages?: number;
};

type RawImageCandidate = {
    imageUrl: string;
    sourcePage: string;
    evidence: string;
    isSocialPreview: boolean;
};

const LIKELY_PAGE_RE =
    /\b(about|venue|gallery|photo|photos|press|media|location|home|info)\b/i;
const IMAGE_EXT_RE = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
// Signals that this image represents the venue brand or space (clubs want these).
const BRAND_RE = /\b(logo|wordmark|brand|crest|emblem|monogram)\b/i;
const VENUE_RE =
    /\b(banner|hero|venue|interior|exterior|stage|marquee|building|storefront|room|cover)\b/i;
// Comedian-portrait signals — penalized for clubs (a person, not the venue).
const PORTRAIT_RE = /\b(headshot|portrait|comedian|performer|host)\b/i;
const POSTER_RE = /\b(poster|flyer|tour|lineup)\b/i;

const ipv6BlockList = (() => {
    const list = new net.BlockList();
    list.addAddress("::1", "ipv6");
    list.addSubnet("fc00::", 7, "ipv6");
    list.addSubnet("fe80::", 10, "ipv6");
    list.addSubnet("::ffff:0:0", 96, "ipv6");
    return list;
})();

function normalizeUrl(value: string | null | undefined) {
    const trimmed = value?.trim();
    if (!trimmed) return null;

    try {
        const url = new URL(trimmed);
        if (url.protocol !== "http:" && url.protocol !== "https:") {
            return null;
        }
        if (isBlockedHostname(url.hostname)) {
            return null;
        }
        url.hash = "";
        return url.toString();
    } catch {
        return null;
    }
}

function resolveUrl(value: string, baseUrl: string) {
    const trimmed = decodeHtml(value).trim();
    if (
        !trimmed ||
        trimmed.startsWith("data:") ||
        trimmed.startsWith("mailto:")
    ) {
        return null;
    }

    try {
        const url = new URL(trimmed, baseUrl);
        if (url.protocol !== "http:" && url.protocol !== "https:") {
            return null;
        }
        if (isBlockedHostname(url.hostname)) {
            return null;
        }
        url.hash = "";
        return url.toString();
    } catch {
        return null;
    }
}

function isBlockedHostname(hostname: string) {
    const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
    if (!host) return true;
    if (host === "localhost" || host.endsWith(".localhost")) return true;

    if (net.isIPv6(host)) {
        if (ipv6BlockList.check(host, "ipv6")) return true;
        return false;
    }

    if (host === "0.0.0.0") return true;

    // WHATWG URL parsing canonicalizes integer/octal/hex IPv4 forms before
    // this check, so valid IPv4 hosts are dotted-decimal here.
    const octets = host.split(".").map((part) => Number(part));
    if (
        octets.length !== 4 ||
        octets.some(
            (octet) => !Number.isInteger(octet) || octet < 0 || octet > 255,
        )
    ) {
        return false;
    }

    const [a, b] = octets;
    return (
        a === 10 ||
        a === 127 ||
        (a === 169 && b === 254) ||
        (a === 172 && b >= 16 && b <= 31) ||
        (a === 192 && b === 168)
    );
}

function sameOrigin(url: string, origins: Set<string>) {
    try {
        return origins.has(new URL(url).origin);
    } catch {
        return false;
    }
}

function uniquePush(values: string[], seen: Set<string>, value: string) {
    if (seen.has(value)) return;
    seen.add(value);
    values.push(value);
}

function decodeHtml(value: string) {
    return value
        .replace(/&amp;/g, "&")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">");
}

function getAttr(tag: string, attr: string) {
    const match = tag.match(
        new RegExp(`\\s${attr}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, "i"),
    );
    return match?.[2] ?? match?.[3] ?? match?.[4] ?? null;
}

function parseSrcset(value: string) {
    return value
        .split(",")
        .map((entry) => entry.trim().split(/\s+/)[0])
        .filter(Boolean);
}

function extractLinks(
    html: string,
    pageUrl: string,
    officialOrigins: Set<string>,
) {
    const links: string[] = [];
    const seen = new Set<string>();
    const anchorRe =
        /<a\b[^>]*href\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))[^>]*>([\s\S]*?)<\/a>/gi;

    for (const match of html.matchAll(anchorRe)) {
        const href = match[2] ?? match[3] ?? match[4] ?? "";
        const text = match[5]?.replace(/<[^>]+>/g, " ") ?? "";
        const resolved = resolveUrl(href, pageUrl);
        if (!resolved || !sameOrigin(resolved, officialOrigins)) continue;
        if (!LIKELY_PAGE_RE.test(`${href} ${text}`)) continue;
        uniquePush(links, seen, resolved);
    }

    return links;
}

function extractImages(
    html: string,
    pageUrl: string,
    officialOrigins: Set<string>,
): RawImageCandidate[] {
    const images: RawImageCandidate[] = [];
    const seen = new Set<string>();
    const imageTagRe = /<img\b[^>]*>/gi;
    const metaImageRe =
        /<meta\b[^>]*(?:property|name)\s*=\s*["'](?:og:image|twitter:image)["'][^>]*>/gi;

    function addImage(
        rawUrl: string | null,
        evidence: string,
        isSocialPreview: boolean,
    ) {
        if (!rawUrl) return;
        const resolved = resolveUrl(rawUrl, pageUrl);
        if (!resolved || !sameOrigin(resolved, officialOrigins)) return;
        if (!IMAGE_EXT_RE.test(new URL(resolved).pathname)) return;
        if (seen.has(resolved)) return;
        seen.add(resolved);
        images.push({
            imageUrl: resolved,
            sourcePage: pageUrl,
            evidence,
            isSocialPreview,
        });
    }

    for (const match of html.matchAll(imageTagRe)) {
        const tag = match[0];
        const evidence = [
            getAttr(tag, "alt"),
            getAttr(tag, "title"),
            getAttr(tag, "class"),
            getAttr(tag, "id"),
            getAttr(tag, "src"),
        ]
            .filter(Boolean)
            .join(" ");
        addImage(getAttr(tag, "src"), evidence, false);
        const srcset = getAttr(tag, "srcset");
        if (srcset) {
            for (const src of parseSrcset(srcset)) {
                addImage(src, evidence, false);
            }
        }
    }

    for (const match of html.matchAll(metaImageRe)) {
        const tag = match[0];
        addImage(getAttr(tag, "content"), "social preview image", true);
    }

    return images;
}

function scoreCandidate(
    raw: RawImageCandidate,
    inspected: InspectedImage,
    clubName: string,
) {
    let score = 50;
    const reasons: string[] = [];
    const url = raw.imageUrl.toLowerCase();
    const sourcePage = raw.sourcePage.toLowerCase();
    const evidence = `${url} ${sourcePage} ${raw.evidence}`.toLowerCase();
    const normalizedName = clubName.toLowerCase().replace(/\s+/g, " ");
    const nameTokens = normalizedName
        .split(" ")
        .filter((token) => token.length > 2);

    // Clubs want a strong brand/preview image, so og:image and logos are
    // rewarded here — the inverse of comedian discovery, which penalizes them.
    if (raw.isSocialPreview) {
        score += 60;
        reasons.push("og:image / social preview");
    }
    if (BRAND_RE.test(evidence)) {
        score += 70;
        reasons.push("logo / wordmark signal");
    }
    if (VENUE_RE.test(evidence)) {
        score += 35;
        reasons.push("venue / banner signal");
    }
    if (nameTokens.some((token) => evidence.includes(token))) {
        score += 20;
        reasons.push("club name signal");
    }
    if (inspected.width && inspected.height) {
        // Banners and venue shots read landscape; reward that over portrait.
        if (inspected.width > inspected.height) {
            score += 20;
            reasons.push("landscape orientation");
        }
        if (inspected.width >= 1000 || inspected.height >= 1000) {
            score += 25;
            reasons.push("large banner image");
        } else if (inspected.width >= 600 && inspected.height >= 600) {
            score += 10;
            reasons.push("large image");
        }
        // Favicons and sprite icons are too small to be useful brand assets.
        if (inspected.width < 100 || inspected.height < 100) {
            score -= 40;
            reasons.push("tiny image penalty");
        }
    }
    // Headshots, posters and tour flyers belong to comedians/shows, not the
    // venue identity — penalize them so venue brand imagery ranks higher.
    if (PORTRAIT_RE.test(evidence)) {
        score -= 55;
        reasons.push("portrait / person penalty");
    }
    if (POSTER_RE.test(evidence)) {
        score -= 35;
        reasons.push("poster penalty");
    }

    return {
        imageUrl: raw.imageUrl,
        sourcePage: raw.sourcePage,
        width: inspected.width,
        height: inspected.height,
        mimeType: inspected.mimeType,
        score,
        reasons,
    };
}

async function defaultInspectImage(
    imageUrl: string,
    fetchImpl: typeof fetch,
): Promise<InspectedImage | null> {
    const response = await fetchImpl(imageUrl, {
        headers: {
            accept: "image/avif,image/webp,image/png,image/jpeg,image/*",
        },
        redirect: "error",
    });
    if (!response.ok) return null;

    const mimeType =
        response.headers.get("content-type")?.split(";")[0] ?? null;
    const buffer = Buffer.from(await response.arrayBuffer());
    const metadata = await sharp(buffer).metadata();

    return {
        url: imageUrl,
        width: metadata.width ?? null,
        height: metadata.height ?? null,
        mimeType,
    };
}

export async function discoverClubImageCandidates(
    input: ClubImageDiscoveryInput,
    options: DiscoveryOptions = {},
): Promise<ClubImageDiscoveryResult> {
    const fetchImpl = options.fetch ?? fetch;
    const maxPages = options.maxPages ?? 6;
    const seeds = [input.website, input.websiteScrapingUrl]
        .map(normalizeUrl)
        .filter((url): url is string => Boolean(url));
    const seedPages: string[] = [];
    const seedSeen = new Set<string>();
    for (const seed of seeds) uniquePush(seedPages, seedSeen, seed);

    const officialOrigins = new Set(
        seedPages.map((seed) => new URL(seed).origin),
    );
    const queue = [...seedPages];
    const crawledPages: string[] = [];
    const crawledSeen = new Set<string>();
    const rawCandidates: RawImageCandidate[] = [];
    const rawSeen = new Set<string>();

    while (queue.length > 0 && crawledPages.length < maxPages) {
        const pageUrl = queue.shift();
        if (!pageUrl || crawledSeen.has(pageUrl)) continue;
        crawledSeen.add(pageUrl);

        try {
            const response = await fetchImpl(pageUrl, {
                headers: { accept: "text/html,application/xhtml+xml" },
                redirect: "error",
            });
            const contentType = response.headers.get("content-type") ?? "";
            if (!response.ok || !contentType.toLowerCase().includes("html")) {
                continue;
            }

            const html = await response.text();
            crawledPages.push(pageUrl);

            for (const image of extractImages(html, pageUrl, officialOrigins)) {
                if (rawSeen.has(image.imageUrl)) continue;
                rawSeen.add(image.imageUrl);
                rawCandidates.push(image);
            }

            for (const link of extractLinks(html, pageUrl, officialOrigins)) {
                if (
                    !crawledSeen.has(link) &&
                    queue.length + crawledPages.length < maxPages
                ) {
                    queue.push(link);
                }
            }
        } catch {
            continue;
        }
    }

    const inspectImage =
        options.inspectImage ??
        ((url: string) => defaultInspectImage(url, fetchImpl));
    const candidates: ClubImageCandidate[] = [];
    for (const raw of rawCandidates) {
        try {
            const inspected = await inspectImage(raw.imageUrl);
            if (!inspected) continue;
            candidates.push(scoreCandidate(raw, inspected, input.clubName));
        } catch {
            continue;
        }
    }

    candidates.sort(
        (left, right) =>
            right.score - left.score ||
            left.imageUrl.localeCompare(right.imageUrl),
    );

    return { seedPages, crawledPages, candidates };
}
