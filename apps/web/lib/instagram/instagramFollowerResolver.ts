import { request } from "node:https";
import { HttpsProxyAgent } from "https-proxy-agent";

const INSTAGRAM_API_URL =
    "https://i.instagram.com/api/v1/users/web_profile_info/";
const BROWSER_USER_AGENT =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";
const DEFAULT_TIMEOUT_MS = 20_000;

type FetchProfile = (
    url: URL,
    headers: Record<string, string>,
) => Promise<{ status: number; body: unknown }>;

export type InstagramFollowerResolution =
    | { status: "resolved"; followerCount: number }
    | { status: "not_found" }
    | { status: "failed"; detail: string };

export async function resolveInstagramFollowerCount(
    account: string | null | undefined,
    options: { fetchProfile?: FetchProfile } = {},
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

    try {
        const response = await (options.fetchProfile ?? fetchInstagramProfile)(
            url,
            headers,
        );
        if (response.status === 404) return { status: "not_found" };
        if (response.status < 200 || response.status >= 300) {
            return {
                status: "failed",
                detail: `Instagram returned status ${response.status}`,
            };
        }

        const followerCount = readFollowerCount(response.body);
        if (followerCount === null) {
            return {
                status: "failed",
                detail: "Instagram response did not include a follower count",
            };
        }
        return { status: "resolved", followerCount };
    } catch (error) {
        return {
            status: "failed",
            detail: error instanceof Error ? error.message : String(error),
        };
    }
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
    const timeoutSeconds = Number(process.env.INSTAGRAM_FETCH_TIMEOUT_S);
    const timeoutMs =
        Number.isFinite(timeoutSeconds) && timeoutSeconds > 0
            ? timeoutSeconds * 1_000
            : DEFAULT_TIMEOUT_MS;
    const proxyUrl = process.env.RESIDENTIAL_PROXY_URL;
    const agent = proxyUrl ? new HttpsProxyAgent(proxyUrl) : undefined;

    return new Promise((resolve, reject) => {
        const req = request(
            url,
            { method: "GET", headers, agent },
            (response) => {
                const chunks: Buffer[] = [];
                response.on("data", (chunk: Buffer) => chunks.push(chunk));
                response.on("end", () => {
                    const text = Buffer.concat(chunks).toString("utf8");
                    try {
                        resolve({
                            status: response.statusCode ?? 0,
                            body: text ? JSON.parse(text) : null,
                        });
                    } catch {
                        reject(new Error("Instagram returned invalid JSON"));
                    }
                });
            },
        );
        req.setTimeout(timeoutMs, () => {
            req.destroy(new Error("Instagram request timed out"));
        });
        req.on("error", reject);
        req.end();
    });
}
