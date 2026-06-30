const YOUTUBE_WEBSUB_HUB_URL = "https://pubsubhubbub.appspot.com/";
const YOUTUBE_CHANNEL_FEED_URL =
    "https://www.youtube.com/feeds/videos.xml";
const YOUTUBE_WEBSUB_CALLBACK_PATH = "/api/webhooks/youtube";

// Lease the worker requests from the hub on each subscribe/renew. YouTube's
// PubSubHubbub grants a lease (delivered later on the callback verification GET);
// because the callback is observe-only today (TASK-3529), the worker records an
// EXPECTED lease from this requested value so renewal timing has something to act
// on. A future callback-verification task can overwrite leaseExpiresAt with the
// hub-confirmed value.
export const DEFAULT_REQUESTED_LEASE_SECONDS = 432000; // 5 days
// Renew a subscription once its (expected) lease expires within this window.
export const DEFAULT_RENEW_BEFORE_EXPIRY_SECONDS = 86400; // 1 day

export const SUBSCRIPTION_STATUS = {
    subscribed: "subscribed",
    unsubscribed: "unsubscribed",
    failed: "failed",
} as const;

export type YouTubeWebSubAction =
    | "subscribe"
    | "renew"
    | "unsubscribe"
    | "skip";

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

interface EligibleComedian {
    uuid: string;
    name: string;
    youtubeChannelId: string | null;
}

interface ExistingSubscription {
    id: number;
    comedianId: string;
    youtubeChannelId: string;
    status: string;
    leaseExpiresAt: Date | null;
}

interface YouTubeWebSubSettingRow {
    feedIngestionEnabled: boolean;
}

/** Scalar columns written on a subscribe/renew attempt (assignable to Prisma's
 * YouTubeWebSubSubscription update input — all optional). */
interface SubscriptionWriteFields {
    status: string;
    callbackUrl: string;
    lastSubscribeAttemptAt: Date;
    lastSubscribeStatusCode: number | null;
    lastSubscribeError: string | null;
    leaseSeconds?: number;
    leaseExpiresAt?: Date | null;
    subscribedAt?: Date;
}

/** Create payload = the write fields plus the immutable identity columns
 * (assignable to Prisma's unchecked create input via the scalar comedianId FK). */
interface SubscriptionCreateFields extends SubscriptionWriteFields {
    comedianId: string;
    youtubeChannelId: string;
    topicUrl: string;
}

interface UnsubscribeUpdateFields {
    callbackUrl: string;
    lastSubscribeAttemptAt: Date;
    lastSubscribeStatusCode: number | null;
    lastSubscribeError: string | null;
    status?: string;
    unsubscribedAt?: Date;
}

export interface SubscriptionUpsertArgs {
    where: { youtubeChannelId: string };
    create: SubscriptionCreateFields;
    update: SubscriptionWriteFields;
}

export interface SubscriptionUpdateArgs {
    where: { id: number };
    data: UnsubscribeUpdateFields;
}

// Methods use TS method-signature syntax (not arrow-property syntax) so their
// parameters are compared bivariantly under strictFunctionTypes — that lets the
// concrete PrismaClient delegate satisfy these narrow structural shapes.
export interface YouTubeWebSubWorkerDbClient {
    youTubeWebSubSetting: {
        findFirst(): Promise<YouTubeWebSubSettingRow | null>;
    };
    comedian: {
        findMany(args: {
            where: {
                youtubeChannelId: { not: null };
                youtubeLiveFeedEnabled: true;
            };
            select: {
                uuid: true;
                name: true;
                youtubeChannelId: true;
            };
            orderBy: { id: "asc" };
        }): Promise<EligibleComedian[]>;
    };
    youTubeWebSubSubscription: {
        findMany(args: {
            select: {
                id: true;
                comedianId: true;
                youtubeChannelId: true;
                status: true;
                leaseExpiresAt: true;
            };
        }): Promise<ExistingSubscription[]>;
        upsert(args: SubscriptionUpsertArgs): Promise<unknown>;
        update(args: SubscriptionUpdateArgs): Promise<unknown>;
    };
}

interface YouTubeWebSubLogger {
    warn: (message: string) => void;
}

export interface SyncYouTubeWebSubSubscriptionsOptions {
    dbClient: YouTubeWebSubWorkerDbClient;
    fetchFn?: FetchFn;
    callbackUrl: string;
    logger?: YouTubeWebSubLogger;
    /** Plan actions and persist nothing / call no network when true. */
    dryRun?: boolean;
    /** Injectable clock for deterministic tests. */
    now?: Date;
    requestedLeaseSeconds?: number;
    renewBeforeExpirySeconds?: number;
}

export interface YouTubeWebSubActionResult {
    action: YouTubeWebSubAction;
    comedianId: string | null;
    comedianName: string | null;
    youtubeChannelId: string;
    /** null in dry-run (no network call was made). */
    ok: boolean | null;
    /** Hub HTTP status; null in dry-run or when the request threw. */
    status: number | null;
    error?: string;
}

export interface SyncYouTubeWebSubSubscriptionsResult {
    /** True when global feed ingestion is disabled — nothing was attempted. */
    gated: boolean;
    dryRun: boolean;
    counts: Record<YouTubeWebSubAction, number>;
    /** Actionable (non-skip) results executed or planned. */
    total: number;
    succeeded: number;
    failed: number;
    results: YouTubeWebSubActionResult[];
}

interface PlannedAction {
    action: Exclude<YouTubeWebSubAction, "skip">;
    comedianId: string;
    comedianName: string | null;
    youtubeChannelId: string;
    subscriptionId: number | null;
}

function emptyCounts(): Record<YouTubeWebSubAction, number> {
    return { subscribe: 0, renew: 0, unsubscribe: 0, skip: 0 };
}

/**
 * Gated YouTube WebSub subscription/renewal worker.
 *
 * Gating: no hub or DB writes happen unless the global
 * YouTubeWebSubSetting.feedIngestionEnabled flag is true. Within that gate only
 * comedians with a youtubeChannelId AND youtubeLiveFeedEnabled=true are
 * subscribed/renewed. Subscriptions whose comedian became disabled or lost/changed
 * their channel ID are unsubscribed.
 *
 * Each attempt is persisted to YouTubeWebSubSubscription (status, lease window,
 * last attempt time, hub status code, failure reason). In dry-run mode the worker
 * returns the intended subscribe/renew/unsubscribe plan and performs no network or
 * DB writes.
 */
export async function syncYouTubeWebSubSubscriptions(
    options: SyncYouTubeWebSubSubscriptionsOptions,
): Promise<SyncYouTubeWebSubSubscriptionsResult> {
    const now = options.now ?? new Date();
    const dryRun = options.dryRun ?? false;
    const requestedLeaseSeconds =
        options.requestedLeaseSeconds ?? DEFAULT_REQUESTED_LEASE_SECONDS;
    const renewBeforeExpirySeconds =
        options.renewBeforeExpirySeconds ??
        DEFAULT_RENEW_BEFORE_EXPIRY_SECONDS;
    const fetchFn = options.fetchFn ?? fetch;

    const setting = await options.dbClient.youTubeWebSubSetting.findFirst();
    if (!setting?.feedIngestionEnabled) {
        return {
            gated: true,
            dryRun,
            counts: emptyCounts(),
            total: 0,
            succeeded: 0,
            failed: 0,
            results: [],
        };
    }

    const comedians = await options.dbClient.comedian.findMany({
        where: {
            youtubeChannelId: { not: null },
            youtubeLiveFeedEnabled: true,
        },
        select: { uuid: true, name: true, youtubeChannelId: true },
        orderBy: { id: "asc" },
    });
    const subscriptions =
        await options.dbClient.youTubeWebSubSubscription.findMany({
            select: {
                id: true,
                comedianId: true,
                youtubeChannelId: true,
                status: true,
                leaseExpiresAt: true,
            },
        });

    const subscriptionByChannel = new Map<string, ExistingSubscription>();
    for (const subscription of subscriptions) {
        subscriptionByChannel.set(
            subscription.youtubeChannelId,
            subscription,
        );
    }
    const eligibleChannelIds = new Set<string>();

    const renewThreshold = new Date(
        now.getTime() + renewBeforeExpirySeconds * 1000,
    );

    const counts = emptyCounts();
    const plan: PlannedAction[] = [];

    for (const comedian of comedians) {
        if (!comedian.youtubeChannelId) {
            continue;
        }
        const channelId = comedian.youtubeChannelId;
        eligibleChannelIds.add(channelId);

        const existing = subscriptionByChannel.get(channelId);
        if (
            !existing ||
            existing.status !== SUBSCRIPTION_STATUS.subscribed
        ) {
            counts.subscribe += 1;
            plan.push({
                action: "subscribe",
                comedianId: comedian.uuid,
                comedianName: comedian.name,
                youtubeChannelId: channelId,
                subscriptionId: existing?.id ?? null,
            });
        } else if (
            existing.leaseExpiresAt === null ||
            existing.leaseExpiresAt <= renewThreshold
        ) {
            counts.renew += 1;
            plan.push({
                action: "renew",
                comedianId: comedian.uuid,
                comedianName: comedian.name,
                youtubeChannelId: channelId,
                subscriptionId: existing.id,
            });
        } else {
            counts.skip += 1;
        }
    }

    // Unsubscribe still-active subscriptions whose comedian is no longer eligible
    // (disabled flag, or channel ID removed/changed). Only act on rows we believe
    // the hub still has an active lease for — never-subscribed (failed) rows need
    // no hub-side teardown, so they are left untouched.
    for (const subscription of subscriptions) {
        if (
            subscription.status === SUBSCRIPTION_STATUS.subscribed &&
            !eligibleChannelIds.has(subscription.youtubeChannelId)
        ) {
            counts.unsubscribe += 1;
            plan.push({
                action: "unsubscribe",
                comedianId: subscription.comedianId,
                comedianName: null,
                youtubeChannelId: subscription.youtubeChannelId,
                subscriptionId: subscription.id,
            });
        }
    }

    if (dryRun) {
        return {
            gated: false,
            dryRun: true,
            counts,
            total: plan.length,
            succeeded: 0,
            failed: 0,
            results: plan.map((planned) => ({
                action: planned.action,
                comedianId: planned.comedianId,
                comedianName: planned.comedianName,
                youtubeChannelId: planned.youtubeChannelId,
                ok: null,
                status: null,
            })),
        };
    }

    const results: YouTubeWebSubActionResult[] = [];
    for (const planned of plan) {
        results.push(
            await executePlannedAction(planned, {
                fetchFn,
                callbackUrl: options.callbackUrl,
                logger: options.logger,
                dbClient: options.dbClient,
                now,
                requestedLeaseSeconds,
            }),
        );
    }

    return {
        gated: false,
        dryRun: false,
        counts,
        total: results.length,
        succeeded: results.filter((result) => result.ok === true).length,
        failed: results.filter((result) => result.ok === false).length,
        results,
    };
}

interface ExecuteContext {
    fetchFn: FetchFn;
    callbackUrl: string;
    logger?: YouTubeWebSubLogger;
    dbClient: YouTubeWebSubWorkerDbClient;
    now: Date;
    requestedLeaseSeconds: number;
}

async function executePlannedAction(
    planned: PlannedAction,
    ctx: ExecuteContext,
): Promise<YouTubeWebSubActionResult> {
    const channelId = planned.youtubeChannelId;
    const hubMode = planned.action === "unsubscribe" ? "unsubscribe" : "subscribe";

    try {
        const response = await ctx.fetchFn(YOUTUBE_WEBSUB_HUB_URL, {
            method: "POST",
            headers: {
                "content-type": "application/x-www-form-urlencoded",
            },
            body: buildHubBody(hubMode, channelId, ctx.callbackUrl, {
                leaseSeconds:
                    hubMode === "subscribe"
                        ? ctx.requestedLeaseSeconds
                        : undefined,
            }).toString(),
        });

        const error = response.ok
            ? undefined
            : `hub returned status ${response.status}`;
        if (error) {
            ctx.logger?.warn(
                `[youtube-websub-worker] ${planned.action} failed channel ${channelId}: ${error}`,
            );
        }

        await persistAttempt(planned, ctx, {
            ok: response.ok,
            statusCode: response.status,
            error,
        });

        return {
            action: planned.action,
            comedianId: planned.comedianId,
            comedianName: planned.comedianName,
            youtubeChannelId: channelId,
            ok: response.ok,
            status: response.status,
            ...(error ? { error } : {}),
        };
    } catch (caught) {
        const message = getErrorMessage(caught);
        ctx.logger?.warn(
            `[youtube-websub-worker] ${planned.action} failed channel ${channelId}: ${message}`,
        );
        try {
            await persistAttempt(planned, ctx, {
                ok: false,
                statusCode: null,
                error: message,
            });
        } catch (persistError) {
            ctx.logger?.warn(
                `[youtube-websub-worker] failed to persist ${planned.action} for channel ${channelId}: ${getErrorMessage(persistError)}`,
            );
        }
        return {
            action: planned.action,
            comedianId: planned.comedianId,
            comedianName: planned.comedianName,
            youtubeChannelId: channelId,
            ok: false,
            status: null,
            error: message,
        };
    }
}

interface AttemptOutcome {
    ok: boolean;
    statusCode: number | null;
    error: string | undefined;
}

async function persistAttempt(
    planned: PlannedAction,
    ctx: ExecuteContext,
    outcome: AttemptOutcome,
): Promise<void> {
    const channelId = planned.youtubeChannelId;
    const topicUrl = buildYouTubeFeedTopicUrl(channelId);

    if (planned.action === "unsubscribe") {
        if (planned.subscriptionId === null) {
            return;
        }
        // On a failed teardown leave status=subscribed so the next run retries;
        // only flip to unsubscribed once the hub accepts the request.
        const data: UnsubscribeUpdateFields = {
            callbackUrl: ctx.callbackUrl,
            lastSubscribeAttemptAt: ctx.now,
            lastSubscribeStatusCode: outcome.statusCode,
            lastSubscribeError: outcome.error ?? null,
            ...(outcome.ok
                ? {
                      status: SUBSCRIPTION_STATUS.unsubscribed,
                      unsubscribedAt: ctx.now,
                  }
                : {}),
        };
        await ctx.dbClient.youTubeWebSubSubscription.update({
            where: { id: planned.subscriptionId },
            data,
        });
        return;
    }

    // subscribe / renew
    const status = outcome.ok
        ? SUBSCRIPTION_STATUS.subscribed
        : SUBSCRIPTION_STATUS.failed;

    const writeFields: SubscriptionWriteFields = {
        status,
        callbackUrl: ctx.callbackUrl,
        lastSubscribeAttemptAt: ctx.now,
        lastSubscribeStatusCode: outcome.statusCode,
        lastSubscribeError: outcome.error ?? null,
        ...(outcome.ok
            ? {
                  leaseSeconds: ctx.requestedLeaseSeconds,
                  leaseExpiresAt: new Date(
                      ctx.now.getTime() + ctx.requestedLeaseSeconds * 1000,
                  ),
                  subscribedAt: ctx.now,
              }
            : {}),
    };

    await ctx.dbClient.youTubeWebSubSubscription.upsert({
        where: { youtubeChannelId: channelId },
        create: {
            comedianId: planned.comedianId,
            youtubeChannelId: channelId,
            topicUrl,
            ...writeFields,
        },
        update: writeFields,
    });
}

function buildHubBody(
    mode: "subscribe" | "unsubscribe",
    youtubeChannelId: string,
    callbackUrl: string,
    opts: { leaseSeconds?: number } = {},
): URLSearchParams {
    const params = new URLSearchParams({
        "hub.mode": mode,
        "hub.topic": buildYouTubeFeedTopicUrl(youtubeChannelId),
        "hub.callback": callbackUrl,
        "hub.verify": "async",
    });
    if (opts.leaseSeconds !== undefined) {
        params.set("hub.lease_seconds", String(opts.leaseSeconds));
    }
    return params;
}

export function resolveYouTubeWebSubCallbackUrl(
    env: Record<string, string | undefined> = process.env,
): string {
    if (env.YOUTUBE_WEBSUB_CALLBACK_URL) {
        return env.YOUTUBE_WEBSUB_CALLBACK_URL;
    }

    if (!env.NEXT_PUBLIC_WEBSITE_URL) {
        throw new Error(
            "YOUTUBE_WEBSUB_CALLBACK_URL or NEXT_PUBLIC_WEBSITE_URL must be configured",
        );
    }

    return `${env.NEXT_PUBLIC_WEBSITE_URL.replace(/\/$/, "")}${YOUTUBE_WEBSUB_CALLBACK_PATH}`;
}

export function buildYouTubeFeedTopicUrl(youtubeChannelId: string): string {
    const url = new URL(YOUTUBE_CHANNEL_FEED_URL);
    url.searchParams.set("channel_id", youtubeChannelId);
    return url.toString();
}

function getErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message) {
        return error.message;
    }

    return String(error);
}
