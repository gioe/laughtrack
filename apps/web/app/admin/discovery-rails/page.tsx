import AdminDiscoveryRailPolicyEditor from "@/ui/pages/admin/discovery-rails/AdminDiscoveryRailPolicyEditor";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default function AdminDiscoveryRailsPage() {
    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Discover Rails"
                title="Discover rail policies"
                description="Review and safely tune the rail order and rotation used by each app. Preview the current and next cycle before publishing a change."
            />

            <AdminDiscoveryRailPolicyEditor />
        </div>
    );
}
