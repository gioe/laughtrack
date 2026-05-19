import { listAdminComedians } from "@/lib/admin/comedianManagement";
import AdminComedianManager from "@/ui/pages/admin/comedians/AdminComedianManager";

export const dynamic = "force-dynamic";

export default async function AdminComediansPage() {
    const comedians = await listAdminComedians();
    const blockedCount = comedians.filter(
        (comedian) => comedian.isBlocked,
    ).length;
    const childCount = comedians.filter((comedian) => comedian.parent).length;

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                    <h1 className="font-chivo text-h1 text-cedar">
                        Admin · Comedians
                    </h1>
                    <p className="mt-2 font-dmSans text-body text-soft-charcoal">
                        {comedians.length} comedians · {blockedCount} blocked ·{" "}
                        {childCount} child profiles
                    </p>
                </div>
            </div>

            <AdminComedianManager comedians={comedians} />
        </div>
    );
}
