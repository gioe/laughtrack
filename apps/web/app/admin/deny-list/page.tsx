import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import { isAdminSession } from "@/lib/auth/requireAdmin";
import AdminDenyListManager, {
    type AdminDenyListEntry,
} from "@/ui/pages/admin/deny-list/AdminDenyListManager";
import { Button } from "@/ui/components/ui/button";

export const dynamic = "force-dynamic";

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

function serializeRow(row: DenyListRow): AdminDenyListEntry {
    return {
        name: row.name,
        reason: row.reason,
        addedBy: row.added_by,
        addedAt:
            row.deleted_at instanceof Date
                ? row.deleted_at.toISOString()
                : new Date(row.deleted_at).toISOString(),
    };
}

export default async function AdminDenyListPage(props: {
    searchParams: Promise<{ q?: string }>;
}) {
    if (!(await isAdminSession())) notFound();

    const { q = "" } = await props.searchParams;
    const query = q.trim();

    const rows = query
        ? await db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
            WHERE name ILIKE ${`%${query}%`}
               OR reason ILIKE ${`%${query}%`}
               OR added_by ILIKE ${`%${query}%`}
            ORDER BY deleted_at DESC, name ASC
            LIMIT 200
        `
        : await db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
            ORDER BY deleted_at DESC, name ASC
            LIMIT 200
        `;

    const entries = rows.map(serializeRow);

    return (
        <div className="max-w-5xl mx-auto px-4 py-8">
            <div className="mb-4 text-sm">
                <Link
                    href="/admin/clubs"
                    className="text-copper-dark hover:underline"
                >
                    ← Admin clubs
                </Link>
            </div>
            <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                    <h1 className="text-2xl font-bold mb-1">
                        Admin · Deny List
                    </h1>
                    <p className="text-sm text-gray-700">
                        {entries.length} entr
                        {entries.length === 1 ? "y" : "ies"}
                        {query ? ` matching "${query}"` : ""}
                    </p>
                </div>
                <form method="get" className="flex gap-2 md:min-w-[360px]">
                    <input
                        type="text"
                        name="q"
                        defaultValue={query}
                        placeholder="Search name, reason, actor"
                        className="min-w-0 flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                    />
                    <Button type="submit" variant="roundedShimmer">
                        Search
                    </Button>
                </form>
            </div>

            <AdminDenyListManager entries={entries} />
        </div>
    );
}
