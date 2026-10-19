import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import CurationWorkspace from "@/ui/pages/admin/reviews/CurationWorkspace";
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
            <CurationWorkspace initialFilters={initialFilters} />
        </div>
    );
}
