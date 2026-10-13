import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import ReviewWorkspace from "@/ui/pages/admin/reviews/ReviewWorkspace";
export default async function ReviewsPage({
    searchParams,
}: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
    const params = await searchParams;
    const initialFilters = Object.fromEntries(
        Object.entries(params).filter(
            (entry): entry is [string, string] => typeof entry[1] === "string",
        ),
    );
    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin"
                title="Review inbox"
                description="Check the source, resolve matches, and approve what belongs in LaughTrack."
            />
            <ReviewWorkspace initialFilters={initialFilters} />
        </div>
    );
}
