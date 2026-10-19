export const button =
    "rounded-md border border-strong px-3 py-2 font-semibold hover:bg-surface-elevated focus-visible:outline focus-visible:outline-2 focus-visible:outline-copper disabled:opacity-40";
export const field =
    "w-full min-w-0 rounded-md border border-input bg-background p-2 text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-copper";
export async function inboxRequest<T>(
    url: string,
    body?: unknown,
    signal?: AbortSignal,
): Promise<T> {
    const response = await fetch(url, {
        method: body ? "POST" : "GET",
        ...(body
            ? {
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(body),
              }
            : {}),
        signal,
    });
    const data = await response.json();
    if (!response.ok)
        throw Object.assign(
            new Error(data.error ?? "Unable to complete review."),
            { status: response.status },
        );
    return data;
}
