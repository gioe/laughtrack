import { getYouTubeWebSubSettings } from "@/lib/admin/youtubeWebSub";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
import AdminFeatureFlagsManager from "@/ui/pages/admin/feature-flags/AdminFeatureFlagsManager";

export const dynamic = "force-dynamic";

export default async function AdminFeatureFlagsPage() {
    const settings = await getYouTubeWebSubSettings();

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Feature Flags"
                title="Feature flags"
                description="Control rollout switches for operational features."
            />

            <AdminFeatureFlagsManager settings={settings} />
        </div>
    );
}
