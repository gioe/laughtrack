import Link from "next/link";
import { listAdminClubGroups } from "@/lib/admin/clubManagement";
import AdminClubManager from "@/ui/pages/admin/clubs/AdminClubManager";

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
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                    <h1 className="font-chivo text-h1 text-cedar">
                        Admin · Clubs
                    </h1>
                    <p className="mt-2 font-dmSans text-body text-soft-charcoal">
                        {clubCount.toLocaleString()} clubs ·{" "}
                        {chainCount.toLocaleString()} chains ·{" "}
                        {hiddenCount.toLocaleString()} hidden ·{" "}
                        {closedCount.toLocaleString()} closed
                    </p>
                </div>
                <Link
                    href="/admin/deny-list"
                    className="font-dmSans text-body font-semibold text-copper-dark hover:underline"
                >
                    Deny list
                </Link>
            </div>

            <AdminClubManager groups={groups} />
        </div>
    );
}
