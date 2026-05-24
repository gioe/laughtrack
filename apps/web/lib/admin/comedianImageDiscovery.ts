import sharp from "sharp";

export type ComedianImageDiscoveryInput = {
    comedianName: string;
    website: string | null;
    websiteScrapingUrl: string | null;
};

export type ComedianImageCandidate = {
    imageUrl: string;
    sourcePage: string;
    width: number | null;
    height: number | null;
    mimeType: string | null;
    score: number;
    reasons: string[];
};

export type ComedianImageDiscoveryResult = {
    seedPages: string[];
    crawledPages: string[];
    candidates: ComedianImageCandidate[];
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
};

const LIKELY_PAGE_RE =
    /\b(about|bio|press|media|photo|photos|gallery|headshot|epk)\b/i;
const IMAGE_EXT_RE = /\.(avif|gif|jpe?g|png|webp)(?:[?#].*)?$/i;
const IMAGE_SIGNAL_RE = /\b(headshot|press|photo|portrait|media|publicity)\b/i;
const POSTER_RE = /\b(poster|flyer|tour|show|event|banner)\b/i;
const LOGO_RE = /\b(logo|icon|favicon|brand|wordmark)\b/i;

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
    if (host === "localhost" || host.endsWith(".localhost")) return true;
    if (host === "::1" || host === "0:0:0:0:0:0:0:1") return true;
    if (host === "0.0.0.0") return true;

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

    function addImage(rawUrl: string | null, evidence: string) {
        if (!rawUrl) return;
        const resolved = resolveUrl(rawUrl, pageUrl);
        if (!resolved || !sameOrigin(resolved, officialOrigins)) return;
        if (!IMAGE_EXT_RE.test(new URL(resolved).pathname)) return;
        if (seen.has(resolved)) return;
        seen.add(resolved);
        images.push({ imageUrl: resolved, sourcePage: pageUrl, evidence });
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
        addImage(getAttr(tag, "src"), evidence);
        const srcset = getAttr(tag, "srcset");
        if (srcset) {
            for (const src of parseSrcset(srcset)) {
                addImage(src, evidence);
            }
        }
    }

    for (const match of html.matchAll(metaImageRe)) {
        const tag = match[0];
        addImage(getAttr(tag, "content"), "social preview image");
    }

    return images;
}

function scoreCandidate(
    raw: RawImageCandidate,
    inspected: InspectedImage,
    comedianName: string,
) {
    let score = 50;
    const reasons: string[] = [];
    const url = raw.imageUrl.toLowerCase();
    const sourcePage = raw.sourcePage.toLowerCase();
    const evidence = `${url} ${sourcePage} ${raw.evidence}`.toLowerCase();
    const normalizedName = comedianName.toLowerCase().replace(/\s+/g, " ");
    const nameTokens = normalizedName
        .split(" ")
        .filter((token) => token.length > 2);

    if (/\bheadshot\b/.test(evidence)) {
        score += 70;
        reasons.push("headshot signal");
    }
    if (/\bpress\b/.test(evidence)) {
        score += 45;
        reasons.push("press signal");
    }
    if (/\b(photo|portrait|publicity|media)\b/.test(evidence)) {
        score += 20;
        reasons.push("photo signal");
    }
    if (nameTokens.some((token) => evidence.includes(token))) {
        score += 15;
        reasons.push("comedian name signal");
    }
    if (inspected.width && inspected.height) {
        if (inspected.height > inspected.width) {
            score += 20;
            reasons.push("portrait orientation");
        }
        if (inspected.width >= 800 && inspected.height >= 800) {
            score += 15;
            reasons.push("large image");
        }
        if (inspected.width < 300 || inspected.height < 300) {
            score -= 35;
            reasons.push("small image penalty");
        }
    }
    if (POSTER_RE.test(evidence)) {
        score -= 35;
        reasons.push("poster penalty");
    }
    if (LOGO_RE.test(evidence)) {
        score -= 80;
        reasons.push("logo penalty");
    }
    if (!IMAGE_SIGNAL_RE.test(evidence)) {
        score -= 5;
        reasons.push("weak image context");
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

export async function discoverComedianImageCandidates(
    input: ComedianImageDiscoveryInput,
    options: DiscoveryOptions = {},
): Promise<ComedianImageDiscoveryResult> {
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
    const candidates: ComedianImageCandidate[] = [];
    for (const raw of rawCandidates) {
        try {
            const inspected = await inspectImage(raw.imageUrl);
            if (!inspected) continue;
            candidates.push(scoreCandidate(raw, inspected, input.comedianName));
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
