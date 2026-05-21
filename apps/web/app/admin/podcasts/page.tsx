import { listPodcastHostshipReviews } from "@/lib/admin/podcastHostshipReviews";
import AdminPodcastHostshipReviewManager from "@/ui/pages/admin/podcasts/AdminPodcastHostshipReviewManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminPodcastHostshipReviewPage() {
    const candidates = await listPodcastHostshipReviews();
    const pendingCount = candidates.filter(
        (candidate) => candidate.candidateStatus === "pending",
    ).length;

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Podcast Reviews"
                title="Podcast hostship"
                description="Review podcast-to-comedian hostship, approved feeds, and candidate matches."
                summary={`${candidates.length.toLocaleString()} total candidate${candidates.length === 1 ? "" : "s"} · ${pendingCount.toLocaleString()} pending`}
            />

            <AdminPodcastHostshipReviewManager candidates={candidates} />
        </div>
    );
}
