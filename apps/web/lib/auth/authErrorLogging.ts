const SENSITIVE_KEY_PATTERN =
    /(?:secret|token|password|authorization|cookie|csrf|pkce|verifier|session|code)/i;

type Jsonish =
    | string
    | number
    | boolean
    | null
    | Jsonish[]
    | { [key: string]: Jsonish };

export function sanitizeAuthError(error: unknown): Jsonish {
    return sanitizeValue(error, 0);
}

function sanitizeValue(value: unknown, depth: number): Jsonish {
    if (depth > 5) return "[truncated]";

    if (
        value === null ||
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
    ) {
        return value;
    }

    if (value instanceof Error) {
        const result: { [key: string]: Jsonish } = {
            name: value.name,
            message: value.message,
        };
        Object.entries(value as Error & Record<string, unknown>).forEach(
            ([key, entry]) => {
                if (key === "name" || key === "message" || key === "stack") {
                    return;
                }
                result[key] = sanitizeEntry(key, entry, depth + 1);
            },
        );
        return result;
    }

    if (Array.isArray(value)) {
        return value.map((entry) => sanitizeValue(entry, depth + 1));
    }

    if (typeof value === "object") {
        return Object.fromEntries(
            Object.entries(value as Record<string, unknown>).map(
                ([key, entry]) => [key, sanitizeEntry(key, entry, depth + 1)],
            ),
        );
    }

    return String(value);
}

function sanitizeEntry(key: string, value: unknown, depth: number): Jsonish {
    if (key === "code" && depth <= 1) return sanitizeValue(value, depth);
    if (SENSITIVE_KEY_PATTERN.test(key)) return "[redacted]";
    return sanitizeValue(value, depth);
}
