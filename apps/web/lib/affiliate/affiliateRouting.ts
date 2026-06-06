export type AffiliateProvider =
    | "ticketmaster"
    | "eventbrite"
    | "tixr"
    | "seatengine"
    | "direct_venue"
    | "malformed";

export type AffiliateFallbackReason =
    | "no_affiliate_rule"
    | "direct_venue"
    | "malformed_url"
    | "unsupported_protocol";

export interface AffiliateRule {
    queryParam: string;
    value: string;
}

export type AffiliateRules = Partial<Record<AffiliateProvider, AffiliateRule>>;

interface ResolveAffiliateDestinationInput {
    destinationUrl: string;
    rules?: AffiliateRules;
}

interface AffiliateDestinationBase {
    provider: AffiliateProvider;
    originalUrl: string | null;
    routedUrl: string | null;
    affiliateApplied: boolean;
    fallbackReason: AffiliateFallbackReason | null;
}

export type AffiliateDestination =
    | (AffiliateDestinationBase & { ok: true })
    | (AffiliateDestinationBase & { ok: false });

const PROVIDER_HOSTS: Array<{
    provider: Exclude<AffiliateProvider, "direct_venue" | "malformed">;
    hosts: string[];
}> = [
    {
        provider: "ticketmaster",
        hosts: ["ticketmaster.com", "ticketweb.com", "livenation.com"],
    },
    { provider: "eventbrite", hosts: ["eventbrite.com"] },
    { provider: "tixr", hosts: ["tixr.com"] },
    { provider: "seatengine", hosts: ["seatengine.com"] },
];

function hostnameMatches(hostname: string, host: string): boolean {
    return hostname === host || hostname.endsWith(`.${host}`);
}

function identifyProvider(url: URL): AffiliateProvider {
    const hostname = url.hostname.toLowerCase();
    for (const candidate of PROVIDER_HOSTS) {
        if (candidate.hosts.some((host) => hostnameMatches(hostname, host))) {
            return candidate.provider;
        }
    }
    return "direct_venue";
}

export function resolveAffiliateDestination({
    destinationUrl,
    rules = {},
}: ResolveAffiliateDestinationInput): AffiliateDestination {
    let parsed: URL;
    try {
        parsed = new URL(destinationUrl);
    } catch {
        return {
            ok: false,
            provider: "malformed",
            originalUrl: null,
            routedUrl: null,
            affiliateApplied: false,
            fallbackReason: "malformed_url",
        };
    }

    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        return {
            ok: false,
            provider: "malformed",
            originalUrl: null,
            routedUrl: null,
            affiliateApplied: false,
            fallbackReason: "unsupported_protocol",
        };
    }

    const originalUrl = parsed.toString();
    const provider = identifyProvider(parsed);
    const rule = rules[provider];

    if (rule) {
        parsed.searchParams.set(rule.queryParam, rule.value);
        return {
            ok: true,
            provider,
            originalUrl,
            routedUrl: parsed.toString(),
            affiliateApplied: true,
            fallbackReason: null,
        };
    }

    return {
        ok: true,
        provider,
        originalUrl,
        routedUrl: originalUrl,
        affiliateApplied: false,
        fallbackReason:
            provider === "direct_venue" ? "direct_venue" : "no_affiliate_rule",
    };
}

export function affiliateRulesFromEnv(): AffiliateRules {
    const ticketmasterCode = process.env.TICKETMASTER_AFFILIATE_CAMEFROM;
    return {
        ...(ticketmasterCode
            ? {
                  ticketmaster: {
                      queryParam: "camefrom",
                      value: ticketmasterCode,
                  },
              }
            : {}),
    };
}
