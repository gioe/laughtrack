import type { AdminPodcastHostshipReviewCandidate } from "@/lib/admin/podcastHostshipReviews";

export type Status = { kind: "idle" | "ok" | "error"; message?: string };

export type ComedianOption = {
    id: number;
    uuid: string;
    name: string;
    popularity: number;
    confidence?: number;
    source?: string;
    associationType?: string | null;
};

export type PodcastReviewGroup = {
    key: string;
    podcast: NonNullable<AdminPodcastHostshipReviewCandidate["podcast"]>;
    candidates: AdminPodcastHostshipReviewCandidate[];
    comedianOptions: ComedianOption[];
    acceptedHost: ComedianOption | null;
    acceptedCohosts: ComedianOption[];
    initialHost: ComedianOption | null;
    initialCohosts: ComedianOption[];
    popularity: number;
};

export type ComedianReviewGroup = {
    key: string;
    comedian: AdminPodcastHostshipReviewCandidate["comedian"];
    candidates: AdminPodcastHostshipReviewCandidate[];
    podcastGroups: PodcastReviewGroup[];
    popularity: number;
};

export type SearchResult = {
    id: number;
    uuid: string;
    name: string;
    popularity?: number;
};

export function formatPercent(value: number) {
    return `${Math.round(value * 100)}%`;
}

export function formatPopularity(value: number) {
    return value.toLocaleString(undefined, {
        maximumFractionDigits: 2,
        minimumFractionDigits: value > 0 && value < 1 ? 2 : 1,
    });
}

export function formatAssociationType(value?: string | null) {
    return value ? `Suggested: ${value}` : "Suggested role unknown";
}

export function formatDate(iso: string) {
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

export function evidencePreview(evidence: unknown) {
    if (!evidence || typeof evidence !== "object") return "No evidence";
    return JSON.stringify(evidence, null, 2);
}
