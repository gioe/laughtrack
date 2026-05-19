import { listAdminPipelines } from "@/lib/admin/pipelines";
import AdminPipelineRunsTable from "@/ui/pages/admin/pipelines/AdminPipelineRunsTable";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminPipelinesPage() {
    const data = await listAdminPipelines();

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Pipelines"
                title="Pipeline runs"
                description="Recent operational runs from scraper metrics and GitHub Actions."
            />

            <AdminPipelineRunsTable runs={data.recentRuns} />
        </div>
    );
}
