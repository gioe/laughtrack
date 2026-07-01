import { listYouTubeWebSubEvents } from "@/lib/admin/youtubeWebSub";
import AdminYouTubeWebSubManager from "@/ui/pages/admin/youtube-websub/AdminYouTubeWebSubManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminYouTubeWebSubPage() {
    const events = await listYouTubeWebSubEvents();

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · YouTube WebSub"
                title="YouTube live feeds"
                description="Inspect comedian subscription state and review what YouTube has sent."
            />

            <AdminYouTubeWebSubManager events={events} />
        </div>
    );
}
