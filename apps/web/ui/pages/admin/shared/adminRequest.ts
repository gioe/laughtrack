export type AdminRequestOptions = {
    httpErrorMessage?: string;
    networkErrorMessage?: string | ((error: unknown) => string);
};

type ApiErrorBody = {
    error?: unknown;
};

export async function adminRequest<T = void>(
    input: RequestInfo | URL,
    init?: RequestInit,
    options: AdminRequestOptions = {},
): Promise<T> {
    let response: Response;
    try {
        response = await fetch(input, init);
    } catch (error) {
        const configuredMessage = options.networkErrorMessage;
        const message =
            typeof configuredMessage === "function"
                ? configuredMessage(error)
                : (configuredMessage ??
                  (error instanceof Error ? error.message : "Network error"));
        throw new Error(message);
    }

    const body: unknown =
        typeof response.json === "function"
            ? await response.json().catch(() => undefined)
            : undefined;

    if (!response.ok) {
        const errorValue =
            body !== null && typeof body === "object"
                ? (body as ApiErrorBody).error
                : undefined;
        const apiError =
            typeof errorValue === "string" ? errorValue : undefined;

        throw new Error(
            apiError ??
                options.httpErrorMessage ??
                `Request failed (${response.status})`,
        );
    }

    return body as T;
}
