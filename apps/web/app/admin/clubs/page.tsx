import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import { isAdminSession } from "@/lib/auth/requireAdmin";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 50;

export default async function AdminClubsPage(props: {
    searchParams: Promise<{ q?: string; page?: string }>;
}) {
    if (!(await isAdminSession())) notFound();

    const { q = "", page: pageRaw } = await props.searchParams;
    const page = Math.max(0, Number(pageRaw) || 0);
    const query = q.trim();

    const where = query
        ? { name: { contains: query, mode: "insensitive" as const } }
        : {};

    const [clubs, total] = await Promise.all([
        db.club.findMany({
            where,
            orderBy: { name: "asc" },
            skip: page * PAGE_SIZE,
            take: PAGE_SIZE,
            select: {
                id: true,
                name: true,
                city: true,
                state: true,
                description: true,
                hours: true,
            },
        }),
        db.club.count({ where }),
    ]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    return (
        <div className="max-w-5xl mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-4">Admin · Clubs</h1>
            <form method="get" className="flex gap-2 mb-6">
                <input
                    type="text"
                    name="q"
                    defaultValue={query}
                    placeholder="Search by name…"
                    className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                />
                <button
                    type="submit"
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-copper text-white font-dmSans font-bold text-base shadow-sm hover:bg-copper/90 hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                >
                    Search
                </button>
            </form>

            <p className="text-sm text-gray-700 mb-2">
                {total} club{total === 1 ? "" : "s"} · page {page + 1} of{" "}
                {totalPages}
            </p>

            <ul className="divide-y divide-gray-300">
                {clubs.map((club) => {
                    const hasDescription =
                        typeof club.description === "string" &&
                        club.description.trim() !== "";
                    const hasHours =
                        club.hours !== null && club.hours !== undefined;
                    return (
                        <li
                            key={club.id}
                            className="py-3 flex items-center justify-between"
                        >
                            <div>
                                <Link
                                    href={`/admin/clubs/${club.id}`}
                                    className="font-semibold hover:underline"
                                >
                                    {club.name}
                                </Link>
                                <div className="text-sm text-gray-700">
                                    {[club.city, club.state]
                                        .filter(Boolean)
                                        .join(", ") || "—"}
                                </div>
                            </div>
                            <div className="text-xs flex gap-3">
                                <span
                                    className={
                                        hasDescription
                                            ? "text-green-600"
                                            : "text-amber-600"
                                    }
                                >
                                    {hasDescription ? "✓" : "—"} description
                                </span>
                                <span
                                    className={
                                        hasHours
                                            ? "text-green-600"
                                            : "text-amber-600"
                                    }
                                >
                                    {hasHours ? "✓" : "—"} hours
                                </span>
                            </div>
                        </li>
                    );
                })}
            </ul>

            {totalPages > 1 && (
                <nav className="flex justify-between mt-6">
                    <PaginationLink
                        label="← Prev"
                        disabled={page === 0}
                        q={query}
                        page={page - 1}
                    />
                    <PaginationLink
                        label="Next →"
                        disabled={page + 1 >= totalPages}
                        q={query}
                        page={page + 1}
                    />
                </nav>
            )}
        </div>
    );
}

function PaginationLink({
    label,
    q,
    page,
    disabled,
}: {
    label: string;
    q: string;
    page: number;
    disabled: boolean;
}) {
    if (disabled) {
        return (
            <span className="inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium opacity-50 cursor-not-allowed bg-gray-100">
                {label}
            </span>
        );
    }
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (page > 0) params.set("page", String(page));
    const qs = params.toString();
    return (
        <Link
            href={`/admin/clubs${qs ? `?${qs}` : ""}`}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-400 rounded-md text-sm font-medium hover:bg-gray-100 transition-colors"
        >
            {label}
        </Link>
    );
}
