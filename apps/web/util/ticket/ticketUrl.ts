export function validTicketUrl(
    value: string | null | undefined,
): string | null {
    const trimmed = value?.trim();
    if (!trimmed) return null;
    try {
        const url = new URL(trimmed);
        return url.protocol === "http:" || url.protocol === "https:"
            ? url.href
            : null;
    } catch {
        return null;
    }
}
