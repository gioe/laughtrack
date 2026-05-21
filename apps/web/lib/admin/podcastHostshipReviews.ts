import {
    listPodcastOwnershipReviews,
    type AdminPodcastOwnershipReviewCandidate,
} from "@/lib/admin/podcastOwnershipReviews";

export type AdminPodcastHostshipReviewCandidate = Omit<
    AdminPodcastOwnershipReviewCandidate,
    "existingOwnerships"
> & {
    existingHostships: AdminPodcastOwnershipReviewCandidate["existingOwnerships"];
};

export async function listPodcastHostshipReviews(): Promise<
    AdminPodcastHostshipReviewCandidate[]
> {
    const candidates = await listPodcastOwnershipReviews();
    return candidates.map(({ existingOwnerships, ...candidate }) => ({
        ...candidate,
        existingHostships: existingOwnerships,
    }));
}
