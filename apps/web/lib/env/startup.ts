import "server-only";

type Env = Record<string, string | undefined>;

type RequiredEnvGroup = {
    label: string;
    names: string[];
};

type StartupEnvValidationOptions = {
    env?: Env;
    logger?: Pick<Console, "error">;
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
    },
    {
        label: "AUTH_GOOGLE_SECRET or GOOGLE_CLIENT_SECRET",
        names: ["AUTH_GOOGLE_SECRET", "GOOGLE_CLIENT_SECRET", "GOOGLE_SECRET"],
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

export function getMissingStartupEnv(env: Env = process.env) {
    return REQUIRED_ENV_GROUPS.filter(
        (group) => !group.names.some((name) => hasValue(env, name)),
    ).map((group) => group.label);
}

export function validateWebStartupEnv({
    env = process.env,
    logger = console,
}: StartupEnvValidationOptions = {}) {
    const missing = getMissingStartupEnv(env);
    if (missing.length === 0) return;

    const error = new MissingStartupEnvError(missing);
    logger.error(error.message);
    throw error;
}
