import { Impit } from "impit";

const INSTAGRAM_API_URL =
    "https://i.instagram.com/api/v1/users/web_profile_info/";
const INSTAGRAM_PROFILE_URL = "https://www.instagram.com/";
const BROWSER_USER_AGENT =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";
const DEFAULT_TIMEOUT_MS = 20_000;
const DEFAULT_FETCH_ATTEMPTS = 4;
const MAX_FETCH_ATTEMPTS = 10;
const DEFAULT_REQUEST_DELAY_MS = 1_000;
const NOT_FOUND_CONFIRMATIONS = 2;

type FetchProfile = (
    url: URL,
    headers: Record<string, string>,
) => Promise<{ status: number; body: unknown }>;

type FetchProfileHtml = (
    url: URL,
    headers: Record<string, string>,
) => Promise<{ status: number; body: string }>;

type TerminalFailure =
    | "http_error"
    | "malformed_response"
    | "network_error"
    | "unconfirmed_not_found";

type Warn = (message: string) => void;

type ResolverOptions = {
    fetchProfile?: FetchProfile;
    fetchProfileHtml?: FetchProfileHtml;
    sleep?: (delayMs: number) => Promise<void>;
    warn?: Warn;
};

export type InstagramFollowerResolution =
    | { status: "resolved"; followerCount: number }
    | { status: "not_found" }
    | { status: "failed"; detail: string };

export async function resolveInstagramFollowerCount(
    account: string | null | undefined,
    options: ResolverOptions = {},
): Promise<InstagramFollowerResolution> {
    const normalizedAccount = account?.trim().replace(/^@/, "");
    if (!normalizedAccount) {
        return { status: "failed", detail: "Instagram handle is empty" };
    }

    const url = new URL(INSTAGRAM_API_URL);
    url.searchParams.set("username", normalizedAccount);
    const headers = {
        "X-IG-App-ID": process.env.INSTAGRAM_APP_ID ?? "936619743392459",
        "User-Agent": BROWSER_USER_AGENT,
        Accept: "application/json",
    };
    const attempts = readPositiveInteger(
        process.env.INSTAGRAM_FETCH_ATTEMPTS,
        DEFAULT_FETCH_ATTEMPTS,
        MAX_FETCH_ATTEMPTS,
    );
    const delayMs =
        readPositiveNumber(
            process.env.SOCIAL_REQUEST_DELAY_S,
            DEFAULT_REQUEST_DELAY_MS / 1_000,
        ) * 1_000;
    const fetchProfile = options.fetchProfile ?? fetchInstagramProfile;
    // A custom primary fetch is normally a unit-test seam. Avoid unexpectedly
    // reaching the live HTML endpoint unless its fallback is injected too.
    const fetchProfileHtml =
        options.fetchProfileHtml ??
        (options.fetchProfile ? null : fetchInstagramProfileHtml);
    const sleep = options.sleep ?? wait;
    const warn = options.warn ?? console.warn;

    let notFoundCount = 0;
    let detail = "Instagram request failed";
    let failure: TerminalFailure = "network_error";
    let lastStatus: number | undefined;
    let htmlFallbackAttempted = false;

    for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
            const response = await fetchProfile(url, headers);
            lastStatus = response.status;

            if (response.status === 404) {
                notFoundCount += 1;
                if (notFoundCount >= NOT_FOUND_CONFIRMATIONS) {
                    return { status: "not_found" };
                }
                detail = "Instagram returned an unconfirmed status 404";
                failure = "unconfirmed_not_found";
            } else if (response.status < 200 || response.status >= 300) {
                detail = `Instagram returned status ${response.status}`;
                failure = "http_error";
            } else {
                const followerCount = readFollowerCount(response.body);
                if (followerCount !== null) {
                    return { status: "resolved", followerCount };
                }
                detail = "Instagram response did not include a follower count";
                failure = "malformed_response";
            }
        } catch {
            detail = "Instagram request failed";
            failure = "network_error";
            lastStatus = undefined;
        }

        if (attempt < attempts) {
            await sleep(delayMs);
        }
    }

    if (failure !== "unconfirmed_not_found" && fetchProfileHtml) {
        htmlFallbackAttempted = true;
        const profileUrl = new URL(
            `${encodeURIComponent(normalizedAccount)}/?hl=en`,
            INSTAGRAM_PROFILE_URL,
        );
        try {
            const response = await fetchProfileHtml(profileUrl, {
                "User-Agent": BROWSER_USER_AGENT,
                Accept: "text/html",
            });
            const followerCount =
                response.status >= 200 && response.status < 300
                    ? readFollowerCountFromHtml(response.body)
                    : null;
            if (followerCount !== null) {
                warn(
                    JSON.stringify({
                        level: "warn",
                        message:
                            "Instagram follower resolution used HTML fallback",
                        event: "instagram_follower_resolution_fallback",
                        account: normalizedAccount,
                        primaryFailure: failure,
                        proxyConfigured: Boolean(
                            process.env.RESIDENTIAL_PROXY_URL,
                        ),
                    }),
                );
                return { status: "resolved", followerCount };
            }
        } catch {
            // The terminal warning below records that both sources failed.
        }
    }

    warn(
        JSON.stringify({
            level: "warn",
            message: "Instagram follower resolution failed",
            event: "instagram_follower_resolution_failed",
            account: normalizedAccount,
            attempts,
            failure,
            ...(htmlFallbackAttempted ? { htmlFallbackAttempted: true } : {}),
            proxyConfigured: Boolean(process.env.RESIDENTIAL_PROXY_URL),
            ...(lastStatus === undefined ? {} : { lastStatus }),
        }),
    );
    return { status: "failed", detail };
}

function readFollowerCountFromHtml(body: string): number | null {
    const metaTags = body.match(/<meta\b[^>]*>/gi) ?? [];
    for (const tag of metaTags) {
        const property = readHtmlAttribute(tag, "property")?.toLowerCase();
        const name = readHtmlAttribute(tag, "name")?.toLowerCase();
        if (property !== "og:description" && name !== "description") continue;

        const content = readHtmlAttribute(tag, "content");
        if (!content) continue;
        const match = content.match(
            /^\s*([\d,]+(?:\.\d+)?)\s*([KMB])?\s+Followers\b/i,
        );
        if (!match) continue;

        const numericText = match[1].replaceAll(",", "");
        const suffix = match[2]?.toUpperCase();
        if (!suffix && numericText.includes(".")) continue;
        const value = Number(numericText);
        const multiplier =
            suffix === "K"
                ? 1_000
                : suffix === "M"
                  ? 1_000_000
                  : suffix === "B"
                    ? 1_000_000_000
                    : 1;
        const count = Math.round(value * multiplier);
        if (Number.isSafeInteger(count) && count >= 0) return count;
    }
    return null;
}

function readHtmlAttribute(tag: string, attribute: string) {
    const match = tag.match(
        new RegExp(`\\b${attribute}\\s*=\\s*(["'])(.*?)\\1`, "i"),
    );
    return match?.[2] ?? null;
}

function readFollowerCount(body: unknown): number | null {
    if (!body || typeof body !== "object") return null;
    const data = (body as { data?: unknown }).data;
    if (!data || typeof data !== "object") return null;
    const user = (data as { user?: unknown }).user;
    if (!user || typeof user !== "object") return null;
    const edgeFollowedBy = (user as { edge_followed_by?: unknown })
        .edge_followed_by;
    if (!edgeFollowedBy || typeof edgeFollowedBy !== "object") return null;
    const count = (edgeFollowedBy as { count?: unknown }).count;
    return typeof count === "number" &&
        Number.isSafeInteger(count) &&
        count >= 0
        ? count
        : null;
}

async function fetchInstagramProfile(
    url: URL,
    headers: Record<string, string>,
): Promise<{ status: number; body: unknown }> {
    const timeoutSeconds = readPositiveNumber(
        process.env.INSTAGRAM_FETCH_TIMEOUT_S,
        DEFAULT_TIMEOUT_MS / 1_000,
        false,
    );
    const client = new Impit({
        browser: "chrome",
        timeout: timeoutSeconds * 1_000,
        ...(process.env.RESIDENTIAL_PROXY_URL
            ? { proxyUrl: process.env.RESIDENTIAL_PROXY_URL }
            : {}),
    });
    const response = await client.fetch(url, { method: "GET", headers });
    const text = await response.text();
    let body: unknown = null;
    if (text) {
        try {
            body = JSON.parse(text);
        } catch {
            if (response.status >= 200 && response.status < 300) {
                throw new Error("Instagram returned invalid JSON");
            }
        }
    }
    return {
        status: response.status,
        body,
    };
}

async function fetchInstagramProfileHtml(
    url: URL,
    headers: Record<string, string>,
): Promise<{ status: number; body: string }> {
    const timeoutSeconds = readPositiveNumber(
        process.env.INSTAGRAM_FETCH_TIMEOUT_S,
        DEFAULT_TIMEOUT_MS / 1_000,
        false,
    );
    const client = new Impit({
        browser: "chrome",
        timeout: timeoutSeconds * 1_000,
        ...(process.env.RESIDENTIAL_PROXY_URL
            ? { proxyUrl: process.env.RESIDENTIAL_PROXY_URL }
            : {}),
    });
    const response = await client.fetch(url, { method: "GET", headers });
    return { status: response.status, body: await response.text() };
}

function readPositiveInteger(
    value: string | undefined,
    fallback: number,
    maximum: number,
): number {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0
        ? Math.min(parsed, maximum)
        : fallback;
}

function readPositiveNumber(
    value: string | undefined,
    fallback: number,
    allowZero = true,
) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && (allowZero ? parsed >= 0 : parsed > 0)
        ? parsed
        : fallback;
}

function wait(delayMs: number) {
    return new Promise<void>((resolve) => setTimeout(resolve, delayMs));
}
