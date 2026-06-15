import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import AdminClubEditor from "@/ui/pages/admin/clubs/AdminClubEditor";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

export default async function AdminClubEditPage(props: {
    params: Promise<{ id: string }>;
}) {
    const { id: idParam } = await props.params;
    const id = Number(idParam);
    if (!Number.isInteger(id) || id <= 0) notFound();

    const club = await db.club.findUnique({
        where: { id },
        select: {
            id: true,
            name: true,
            city: true,
            state: true,
            description: true,
        },
    });

    if (!club) notFound();

    const location = [club.city, club.state].filter(Boolean).join(", ");

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow={`Admin · Clubs · ${club.name}`}
                title="Club details"
                description="Edit venue description."
                summary={location || undefined}
            />

            <div className="max-w-3xl">
                <AdminClubEditor
                    clubId={club.id}
                    clubName={club.name}
                    initialDescription={club.description ?? ""}
                />
            </div>
        </div>
    );
}
