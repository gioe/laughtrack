import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { isAdminSession } from "@/lib/auth/requireAdmin";
import AdminDenyListManager, {
    type AdminDenyListEntry,
} from "@/ui/pages/admin/deny-list/AdminDenyListManager";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";
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
    const entryLabel = `${entries.length.toLocaleString()} entr${entries.length === 1 ? "y" : "ies"}`;
    const summary = query
        ? `${entryLabel} matching "${query}"`
        : entryLabel;

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · Deny List"
                title="Comedian deny list"
                description="Names blocked from ingest. Add a new entry to suppress future scrapes, or remove an entry to allow re-ingest."
                summary={summary}
            />

            <form
                method="get"
                className="grid gap-3 rounded-md border border-copper/25 bg-white p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end"
            >
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Search
                    <input
                        type="search"
                        name="q"
                        defaultValue={query}
                        placeholder="Search name, reason, actor"
                        className="w-full rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                    />
                </label>
                <Button type="submit" variant="roundedShimmer">
                    Search
                </Button>
            </form>

            <AdminDenyListManager entries={entries} />
        </div>
    );
}
