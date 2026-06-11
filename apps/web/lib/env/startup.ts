import "server-only";

type Env = Record<string, string | undefined>;

type RequiredEnvGroup = {
    label: string;
    names: string[];
    // Local sign-in is intentionally disabled (dev OAuth clients were never
    // re-provisioned after the TASK-2334 credential rotation), so `next dev`
    // boots without these — the dev server exists for visual verification
    // against real data, not for exercising the OAuth flow. Only
    // NODE_ENV === "development" gets the exemption; `next start`, Vercel
    // builds, and an unset NODE_ENV all still validate fully.
    optionalInDevelopment?: boolean;
};

type StartupEnvValidationOptions = {
    env?: Env;
    logger?: Pick<Console, "error" | "warn">;
};

const REQUIRED_ENV_GROUPS: RequiredEnvGroup[] = [
    { label: "DATABASE_URL", names: ["DATABASE_URL"] },
    {
        label: "AUTH_SECRET or NEXTAUTH_SECRET",
        names: ["AUTH_SECRET", "NEXTAUTH_SECRET"],
    },
    {
        label: "AUTH_GOOGLE_ID or GOOGLE_CLIENT_ID",
        names: ["AUTH_GOOGLE_ID", "GOOGLE_CLIENT_ID", "GOOGLE_ID"],
        optionalInDevelopment: true,
    },
    {
        label: "AUTH_GOOGLE_SECRET or GOOGLE_CLIENT_SECRET",
        names: ["AUTH_GOOGLE_SECRET", "GOOGLE_CLIENT_SECRET", "GOOGLE_SECRET"],
        optionalInDevelopment: true,
    },
];

export class MissingStartupEnvError extends Error {
    readonly missing: string[];

    constructor(missing: string[]) {
        super(
            `Missing required web startup environment variables: ${missing.join(", ")}`,
        );
        this.name = "MissingStartupEnvError";
        this.missing = missing;
    }
}

function hasValue(env: Env, name: string) {
    return typeof env[name] === "string" && env[name]!.trim().length > 0;
}

function isMissing(env: Env, group: RequiredEnvGroup) {
    return !group.names.some((name) => hasValue(env, name));
}

export function getMissingStartupEnv(env: Env = process.env) {
    const isDevelopment = env.NODE_ENV === "development";
    return REQUIRED_ENV_GROUPS.filter(
        (group) => !(isDevelopment && group.optionalInDevelopment),
    )
        .filter((group) => isMissing(env, group))
        .map((group) => group.label);
}

export function validateWebStartupEnv({
    env = process.env,
    logger = console,
}: StartupEnvValidationOptions = {}) {
    // Fixture mode (the E2E visual-regression CI job) serves home-page
    // fixtures and bypasses auth(), so it never exercises the DB or Google
    // OAuth creds — requiring them would only block the visual run from
    // booting. Mirror the VERCEL_ENV belt-and-suspenders from app/page.tsx so
    // a stray E2E_FIXTURE_MODE=1 on a Vercel production deploy is NOT honored
    // and still validates fully.
    if (env.VERCEL_ENV !== "production" && env.E2E_FIXTURE_MODE === "1") {
        return;
    }

    const missing = getMissingStartupEnv(env);
    if (missing.length !== 0) {
        const error = new MissingStartupEnvError(missing);
        logger.error(error.message);
        throw error;
    }

    if (env.NODE_ENV === "development") {
        const skipped = REQUIRED_ENV_GROUPS.filter(
            (group) => group.optionalInDevelopment && isMissing(env, group),
        ).map((group) => group.label);
        if (skipped.length > 0) {
            logger.warn(
                `OAuth env vars missing (${skipped.join(", ")}) — sign-in is disabled in this dev server. Production startup still requires them.`,
            );
        }
    }
}
