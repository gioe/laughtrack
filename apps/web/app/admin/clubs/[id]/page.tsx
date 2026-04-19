import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import { isAdminSession } from "@/lib/auth/requireAdmin";
import AdminClubEditor from "@/ui/pages/admin/clubs/AdminClubEditor";

export const dynamic = "force-dynamic";

export default async function AdminClubEditPage(props: {
    params: Promise<{ id: string }>;
}) {
    if (!(await isAdminSession())) notFound();

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
            hours: true,
        },
    });

    if (!club) notFound();

    const initialHours =
        club.hours &&
        typeof club.hours === "object" &&
        !Array.isArray(club.hours)
            ? (club.hours as Record<string, unknown>)
            : null;

    return (
        <div className="max-w-3xl mx-auto px-4 py-8">
            <div className="mb-4 text-sm">
                <Link href="/admin/clubs" className="link">
                    ← All clubs
                </Link>
            </div>
            <h1 className="text-2xl font-bold mb-1">{club.name}</h1>
            <div className="text-sm text-base-content/70 mb-6">
                {[club.city, club.state].filter(Boolean).join(", ") || "—"}
            </div>
            <AdminClubEditor
                clubId={club.id}
                clubName={club.name}
                initialDescription={club.description ?? ""}
                initialHours={initialHours}
            />
        </div>
    );
}
