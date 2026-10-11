import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import EventReviews from "./EventReviews";

export const dynamic = "force-dynamic";
export default function EventReviewsPage() {
    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Event Review"
                title="Event review"
                description="Check whether flagged events belong in LaughTrack. Review the event evidence, then approve, reject or defer an individual occurrence."
            />
            <EventReviews />
        </div>
    );
}
