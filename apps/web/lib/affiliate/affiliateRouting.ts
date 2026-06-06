export type AffiliateProvider =
    | "ticketmaster"
    | "eventbrite"
    | "seatgeek"
    | "tickpick"
    | "vivid_seats"
    | "stubhub"
    | "ticketnetwork"
    | "fever"
    | "gametime"
    | "viator"
    | "tixr"
    | "seatengine"
    | "direct_venue"
    | "malformed";

export type AffiliateFallbackReason =
    | "no_affiliate_rule"
    | "direct_venue"
    | "malformed_url"
    | "unsupported_protocol"
    | "invalid_affiliate_rule";

export type PriorityAffiliateProvider =
    | "ticketmaster"
    | "eventbrite"
    | "seatgeek"
    | "tickpick"
    | "vivid_seats"
    | "stubhub"
    | "ticketnetwork"
    | "fever"
    | "gametime"
    | "viator";

export const PRIORITY_AFFILIATE_PROVIDERS: PriorityAffiliateProvider[] = [
    "ticketmaster",
    "eventbrite",
    "seatgeek",
    "tickpick",
    "vivid_seats",
    "stubhub",
    "ticketnetwork",
    "fever",
    "gametime",
    "viator",
];

export interface AffiliateQueryRule {
    type: "query";
    queryParam: string;
    value: string;
    extraParams?: Record<string, string>;
}

export interface AffiliateRedirectRule {
    type: "redirect";
    baseUrl: string;
    urlParam: string;
}

export interface LegacyAffiliateQueryRule {
    queryParam: string;
    value: string;
}

export type AffiliateRule =
    | AffiliateQueryRule
    | AffiliateRedirectRule
    | LegacyAffiliateQueryRule;

export type AffiliateRules = Partial<
    Record<
        Exclude<AffiliateProvider, "direct_venue" | "malformed">,
        AffiliateRule
    >
>;

export interface PriorityAffiliateProgram {
    provider: PriorityAffiliateProvider;
    displayName: string;
    networkName: string;
    envVars: string[];
    launchStatus:
        | "configured_when_env_present"
        | "requires_account_approval"
        | "requires_publisher_ids";
}

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
    { provider: "seatgeek", hosts: ["seatgeek.com"] },
    { provider: "tickpick", hosts: ["tickpick.com"] },
    { provider: "vivid_seats", hosts: ["vividseats.com"] },
    { provider: "stubhub", hosts: ["stubhub.com", "viagogo.com"] },
    { provider: "ticketnetwork", hosts: ["ticketnetwork.com"] },
    { provider: "fever", hosts: ["feverup.com"] },
    { provider: "gametime", hosts: ["gametime.co"] },
    { provider: "viator", hosts: ["viator.com"] },
    { provider: "tixr", hosts: ["tixr.com"] },
    {
        provider: "seatengine",
        hosts: [
            "seatengine.com",
            "seatengine.net",
            "seatengine-sites.com",
            "seatengine.cloud",
        ],
    },
];

const PRIORITY_PROGRAMS: PriorityAffiliateProgram[] = [
    {
        provider: "ticketmaster",
        displayName: "Ticketmaster",
        networkName: "Impact",
        envVars: ["TICKETMASTER_AFFILIATE_CAMEFROM"],
        launchStatus: "configured_when_env_present",
    },
    {
        provider: "eventbrite",
        displayName: "Eventbrite",
        networkName: "Eventbrite Affiliates / network-issued link",
        envVars: ["EVENTBRITE_AFFILIATE_CODE"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "seatgeek",
        displayName: "SeatGeek",
        networkName: "Impact",
        envVars: ["SEATGEEK_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "tickpick",
        displayName: "TickPick",
        networkName: "Direct / network-issued link",
        envVars: ["TICKPICK_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "vivid_seats",
        displayName: "Vivid Seats",
        networkName: "Direct / FlexOffers-style network-issued link",
        envVars: ["VIVID_SEATS_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "stubhub",
        displayName: "StubHub / viagogo",
        networkName: "Awin",
        envVars: ["STUBHUB_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "ticketnetwork",
        displayName: "TicketNetwork",
        networkName: "Direct",
        envVars: ["TICKETNETWORK_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "fever",
        displayName: "Fever",
        networkName: "Fever Affiliate Program",
        envVars: ["FEVER_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "gametime",
        displayName: "Gametime",
        networkName: "FlexOffers / Impact-style network-issued link",
        envVars: ["GAMETIME_AFFILIATE_REDIRECT_BASE_URL"],
        launchStatus: "requires_account_approval",
    },
    {
        provider: "viator",
        displayName: "Viator",
        networkName: "Viator Partner Program",
        envVars: ["VIATOR_AFFILIATE_PID", "VIATOR_AFFILIATE_MCID"],
        launchStatus: "requires_publisher_ids",
    },
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

function applyAffiliateRule(
    destination: URL,
    rule: AffiliateRule,
): string | null {
    if (!("type" in rule) || rule.type === "query") {
        destination.searchParams.set(rule.queryParam, rule.value);
        const extraParams =
            "extraParams" in rule ? rule.extraParams : undefined;
        for (const [key, value] of Object.entries(extraParams ?? {})) {
            destination.searchParams.set(key, value);
        }
        return destination.toString();
    }

    let redirectUrl: URL;
    try {
        redirectUrl = new URL(rule.baseUrl);
    } catch {
        return null;
    }
    redirectUrl.searchParams.set(rule.urlParam, destination.toString());
    return redirectUrl.toString();
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
    const rule =
        provider === "direct_venue" || provider === "malformed"
            ? undefined
            : rules[provider];

    if (rule) {
        const routedUrl = applyAffiliateRule(parsed, rule);
        if (!routedUrl) {
            return {
                ok: true,
                provider,
                originalUrl,
                routedUrl: originalUrl,
                affiliateApplied: false,
                fallbackReason: "invalid_affiliate_rule",
            };
        }

        return {
            ok: true,
            provider,
            originalUrl,
            routedUrl,
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

export function getPriorityAffiliatePrograms(): PriorityAffiliateProgram[] {
    return PRIORITY_PROGRAMS.map((program) => ({
        ...program,
        envVars: [...program.envVars],
    }));
}

function readEnv(name: string): string | undefined {
    const value = process.env[name]?.trim();
    return value || undefined;
}

function redirectRuleFromEnv(name: string): AffiliateRedirectRule | undefined {
    const baseUrl = readEnv(name);
    return baseUrl
        ? {
              type: "redirect",
              baseUrl,
              urlParam: "u",
          }
        : undefined;
}

export function affiliateRulesFromEnv(): AffiliateRules {
    const ticketmasterCode = readEnv("TICKETMASTER_AFFILIATE_CAMEFROM");
    const eventbriteCode = readEnv("EVENTBRITE_AFFILIATE_CODE");
    const viatorPid = readEnv("VIATOR_AFFILIATE_PID");
    const viatorMcid = readEnv("VIATOR_AFFILIATE_MCID");

    return {
        ...(ticketmasterCode
            ? {
                  ticketmaster: {
                      type: "query",
                      queryParam: "camefrom",
                      value: ticketmasterCode,
                  },
              }
            : {}),
        ...(eventbriteCode
            ? {
                  eventbrite: {
                      type: "query",
                      queryParam: "aff",
                      value: eventbriteCode,
                  },
              }
            : {}),
        ...(redirectRuleFromEnv("SEATGEEK_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  seatgeek: redirectRuleFromEnv(
                      "SEATGEEK_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("TICKPICK_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  tickpick: redirectRuleFromEnv(
                      "TICKPICK_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("VIVID_SEATS_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  vivid_seats: redirectRuleFromEnv(
                      "VIVID_SEATS_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("STUBHUB_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  stubhub: redirectRuleFromEnv(
                      "STUBHUB_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("TICKETNETWORK_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  ticketnetwork: redirectRuleFromEnv(
                      "TICKETNETWORK_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("FEVER_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  fever: redirectRuleFromEnv(
                      "FEVER_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(redirectRuleFromEnv("GAMETIME_AFFILIATE_REDIRECT_BASE_URL")
            ? {
                  gametime: redirectRuleFromEnv(
                      "GAMETIME_AFFILIATE_REDIRECT_BASE_URL",
                  ),
              }
            : {}),
        ...(viatorPid && viatorMcid
            ? {
                  viator: {
                      type: "query",
                      queryParam: "pid",
                      value: viatorPid,
                      extraParams: { mcid: viatorMcid },
                  },
              }
            : {}),
    };
}
