export type PodcastAppearanceRoleBucket = "host" | "cohost" | "guest";

export function normalizePodcastAppearanceRole(
    role: string | null | undefined,
): PodcastAppearanceRoleBucket {
    const normalized = String(role ?? "")
        .trim()
        .toLowerCase()
        .replace(/[-_\s]+/g, "_");

    if (normalized === "host") return "host";
    if (normalized === "cohost" || normalized === "co_host") return "cohost";

    return "guest";
}
