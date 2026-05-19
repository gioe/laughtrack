import { listAdminClubGroups } from "@/lib/admin/clubManagement";
import AdminClubManager from "@/ui/pages/admin/clubs/AdminClubManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminClubsPage() {
    const groups = await listAdminClubGroups();
    const clubCount = groups.reduce(
        (sum, group) => sum + group.clubs.length,
        0,
    );
    const chainCount = groups.filter((group) => group.chain).length;
    const hiddenCount = groups.reduce(
        (sum, group) =>
            sum + group.clubs.filter((club) => !club.visible).length,
        0,
    );
    const closedCount = groups.reduce(
        (sum, group) =>
            sum + group.clubs.filter((club) => club.status === "closed").length,
        0,
    );

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Clubs"
                title="Club operations"
                description="Review venue identity, chain grouping, scrape coverage, visibility, and operational status."
                summary={`${clubCount.toLocaleString()} clubs · ${chainCount.toLocaleString()} chains · ${hiddenCount.toLocaleString()} hidden · ${closedCount.toLocaleString()} closed`}
            />

            <AdminClubManager groups={groups} />
        </div>
    );
}
