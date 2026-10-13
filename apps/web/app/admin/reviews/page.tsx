import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import ReviewWorkspace from "@/ui/pages/admin/reviews/ReviewWorkspace";
export default function ReviewsPage() {
    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin"
                title="Review inbox"
                description="Check the source, resolve matches, and approve what belongs in LaughTrack."
            />
            <ReviewWorkspace />
        </div>
    );
}
