import { listAdminComedians } from "@/lib/admin/comedianManagement";
import AdminComedianManager from "@/ui/pages/admin/comedians/AdminComedianManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminComediansPage() {
    const { comedians, denyListCount } = await listAdminComedians();
    const blockedCount = comedians.filter(
        (comedian) => comedian.isBlocked,
    ).length;
    const childCount = comedians.filter((comedian) => comedian.parent).length;

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Comedians"
                title="Comedian identity"
                description="Review comedian records, parent-child relationships, and blocklist state."
                summary={`${comedians.length.toLocaleString()} comedians · ${blockedCount.toLocaleString()} blocked records · ${denyListCount.toLocaleString()} deny-listed names · ${childCount.toLocaleString()} child profiles`}
            />

            <AdminComedianManager comedians={comedians} />
        </div>
    );
}
