export function getInitials(name: string | null | undefined): string {
    if (!name) return "";
    const words = name
        .trim()
        .split(/\s+/)
        .map((w) => w.replace(/[^A-Za-z0-9\u00C0-\u024F]/g, ""))
        .filter(Boolean);
    if (words.length === 0) return "";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}
