import { getYouTubeWebSubAdminData } from "@/lib/admin/youtubeWebSub";
import AdminYouTubeWebSubManager from "@/ui/pages/admin/youtube-websub/AdminYouTubeWebSubManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminYouTubeWebSubPage() {
    const data = await getYouTubeWebSubAdminData();

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · YouTube WebSub"
                title="YouTube live feeds"
                description="Manage rollout flags, inspect comedian subscription state, and review what YouTube has sent."
            />

            <AdminYouTubeWebSubManager
                settings={data.settings}
                comedians={data.comedians}
                events={data.events}
            />
        </div>
    );
}
