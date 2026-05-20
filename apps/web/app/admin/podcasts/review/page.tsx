import { listPodcastOwnershipReviews } from "@/lib/admin/podcastOwnershipReviews";
import AdminPodcastOwnershipReviewManager from "@/ui/pages/admin/podcasts/AdminPodcastOwnershipReviewManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminPodcastOwnershipReviewPage() {
    const candidates = await listPodcastOwnershipReviews();
    const pendingCount = candidates.filter(
        (candidate) => candidate.candidateStatus === "pending",
    ).length;

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Podcast Reviews"
                title="Podcast ownership"
                description="Review podcast-to-comedian ownership, approved feeds, and candidate matches."
                summary={`${candidates.length.toLocaleString()} total candidate${candidates.length === 1 ? "" : "s"} · ${pendingCount.toLocaleString()} pending`}
            />

            <AdminPodcastOwnershipReviewManager candidates={candidates} />
        </div>
    );
}
