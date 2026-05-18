import Link from "next/link";
import { listPendingPodcastOwnershipReviews } from "@/lib/admin/podcastOwnershipReviews";
import AdminPodcastOwnershipReviewManager from "@/ui/pages/admin/podcasts/AdminPodcastOwnershipReviewManager";

export const dynamic = "force-dynamic";

export default async function AdminPodcastOwnershipReviewPage() {
    const candidates = await listPendingPodcastOwnershipReviews();

    return (
        <div className="mx-auto max-w-6xl px-4 py-8">
            <div className="mb-4 text-sm">
                <Link
                    href="/admin/overview"
                    className="text-copper hover:underline"
                >
                    Admin overview
                </Link>
            </div>
            <div className="mb-6">
                <h1 className="mb-1 font-gilroy-bold text-h1 text-cedar">
                    Admin · Podcast Reviews
                </h1>
                <p className="font-dmSans text-body text-soft-charcoal">
                    {candidates.length} pending candidate
                    {candidates.length === 1 ? "" : "s"}
                </p>
            </div>

            <AdminPodcastOwnershipReviewManager candidates={candidates} />
        </div>
    );
}
