"use client";

import type {
    AdminClubGroup,
    AdminClubListItem,
} from "@/lib/admin/clubManagement";
import { Button } from "@/ui/components/ui/button";
import {
    ChevronDown,
    ChevronRight,
    ExternalLink,
    Save,
    Search,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

type Props = {
    groups: AdminClubGroup[];
};

type Draft = {
    status: string;
    visible: boolean;
    clubType: string;
    closedAt: string;
};

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

const CLUB_STATUS_OPTIONS = ["active", "closed", "hiatus"];
const CLUB_TYPE_OPTIONS = ["club", "festival", "venue"];

function dateInputValue(iso: string | null) {
    return iso ? iso.slice(0, 10) : "";
}

function formatDate(iso: string | null) {
    if (!iso) return "Never";
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function initialDraft(club: AdminClubListItem): Draft {
    return {
        status: club.status,
        visible: club.visible,
        clubType: club.clubType,
        closedAt: dateInputValue(club.closedAt),
    };
}

function isDirty(club: AdminClubListItem, draft: Draft) {
    return (
        draft.status !== club.status ||
        draft.visible !== club.visible ||
        draft.clubType !== club.clubType ||
        draft.closedAt !== dateInputValue(club.closedAt)
    );
}

function statusBadgeClass(club: AdminClubListItem) {
    if (club.status === "closed") {
        return "border-red-700/30 bg-red-50 text-red-900";
    }
    if (club.status === "hiatus") {
        return "border-amber-700/30 bg-amber-50 text-amber-900";
    }
    if (!club.visible) {
        return "border-gray-500/30 bg-gray-100 text-gray-900";
    }
    return "border-green-700/30 bg-green-50 text-green-900";
}

export default function AdminClubManager({ groups }: Props) {
    const [rows, setRows] = useState(groups);
    const [query, setQuery] = useState("");
    const [drafts, setDrafts] = useState<Record<number, Draft>>({});
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [collapsedGroups, setCollapsedGroups] = useState<
        Record<string, boolean>
    >({});

    const filteredGroups = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        if (!normalizedQuery) return rows;
        return rows
            .map((group) => {
                const clubs = group.clubs.filter((club) =>
                    [
                        club.name,
                        club.city ?? "",
                        club.state ?? "",
                        group.chain?.name ?? "Unchained",
                        club.status,
                        club.clubType,
                    ]
                        .join(" ")
                        .toLowerCase()
                        .includes(normalizedQuery),
                );
                return {
                    ...group,
                    clubs,
                    totals: {
                        clubCount: clubs.length,
                        visibleCount: clubs.filter((club) => club.visible)
                            .length,
                        activeCount: clubs.filter(
                            (club) => club.status === "active",
                        ).length,
                        scrapedShowCount: clubs.reduce(
                            (sum, club) => sum + club.scrapedShowCount,
                            0,
                        ),
                    },
                };
            })
            .filter((group) => group.clubs.length > 0);
    }, [query, rows]);

    const flatClubCount = rows.reduce(
        (sum, group) => sum + group.clubs.length,
        0,
    );
    const scrapedShowCount = rows.reduce(
        (sum, group) => sum + group.totals.scrapedShowCount,
        0,
    );

    function draftFor(club: AdminClubListItem) {
        return drafts[club.id] ?? initialDraft(club);
    }

    function updateDraft(club: AdminClubListItem, patch: Partial<Draft>) {
        setDrafts((current) => ({
            ...current,
            [club.id]: {
                ...draftFor(club),
                ...patch,
            },
        }));
    }

    function replaceClub(updated: AdminClubListItem) {
        setRows((current) =>
            current.map((group) => {
                const clubs = group.clubs.map((club) =>
                    club.id === updated.id ? updated : club,
                );
                return {
                    ...group,
                    clubs,
                    totals: {
                        clubCount: clubs.length,
                        visibleCount: clubs.filter((club) => club.visible)
                            .length,
                        activeCount: clubs.filter(
                            (club) => club.status === "active",
                        ).length,
                        scrapedShowCount: clubs.reduce(
                            (sum, club) => sum + club.scrapedShowCount,
                            0,
                        ),
                    },
                };
            }),
        );
    }

    function toggleGroup(groupKey: string) {
        setCollapsedGroups((current) => ({
            ...current,
            [groupKey]: !current[groupKey],
        }));
    }

    async function saveClub(club: AdminClubListItem) {
        const draft = draftFor(club);
        setStatus({ kind: "idle" });
        setPendingId(club.id);

        let res: Response;
        try {
            res = await fetch(`/api/admin/clubs/${club.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status: draft.status,
                    visible: draft.visible,
                    clubType: draft.clubType,
                    closedAt: draft.closedAt || null,
                }),
            });
        } catch (error) {
            setPendingId(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingId(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        const body = (await res.json()) as { club: AdminClubListItem };
        replaceClub(body.club);
        setDrafts((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${club.name} saved.` });
    }

    return (
        <div className="space-y-5">
            <div className="grid gap-3 rounded-md border border-copper/25 bg-white p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Search clubs
                    <span className="relative">
                        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-soft-charcoal" />
                        <input
                            type="search"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            className="w-full rounded-md border border-soft-charcoal/30 bg-white py-2 pl-10 pr-3 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                            placeholder="Name, city, chain, status"
                        />
                    </span>
                </label>
                <div className="font-dmSans text-body text-soft-charcoal">
                    {flatClubCount.toLocaleString()} clubs ·{" "}
                    {scrapedShowCount.toLocaleString()} scraped shows
                </div>
            </div>

            {status.kind === "ok" && (
                <p className="rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-body text-green-900">
                    {status.message}
                </p>
            )}
            {status.kind === "error" && (
                <p className="rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-body text-red-900">
                    {status.message}
                </p>
            )}

            <div className="space-y-4">
                {filteredGroups.map((group) => (
                    <section
                        key={group.key}
                        className="overflow-hidden rounded-md border border-copper/25 bg-white"
                    >
                        <header className="border-b border-copper/20 bg-cedar px-4 py-3 text-white">
                            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                                <button
                                    type="button"
                                    aria-expanded={!collapsedGroups[group.key]}
                                    aria-controls={`club-chain-${group.key}`}
                                    onClick={() => toggleGroup(group.key)}
                                    className="flex min-w-0 items-start gap-3 text-left"
                                >
                                    <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/10">
                                        {collapsedGroups[group.key] ? (
                                            <ChevronRight className="h-4 w-4" />
                                        ) : (
                                            <ChevronDown className="h-4 w-4" />
                                        )}
                                    </span>
                                    <span className="min-w-0">
                                        <span className="block font-gilroy-bold text-h3 leading-tight">
                                            {group.chain?.name ?? "Unchained"}
                                        </span>
                                        <span className="mt-1 block font-dmSans text-caption text-white/85">
                                            {group.clubs.length} clubs visible
                                            in this view ·{" "}
                                            {group.totals.visibleCount} visible
                                            · {group.totals.activeCount} active
                                            ·{" "}
                                            {group.totals.scrapedShowCount.toLocaleString()}{" "}
                                            scraped shows
                                        </span>
                                    </span>
                                </button>
                                <div className="flex items-center gap-3 pl-10 md:pl-0">
                                    <span className="font-dmSans text-caption font-semibold text-white/75">
                                        {collapsedGroups[group.key]
                                            ? "Closed"
                                            : "Open"}
                                    </span>
                                    {group.chain?.website && (
                                        <a
                                            href={group.chain.website}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-white hover:underline"
                                        >
                                            Chain site
                                            <ExternalLink className="h-3.5 w-3.5" />
                                        </a>
                                    )}
                                </div>
                            </div>
                        </header>

                        <ul
                            id={`club-chain-${group.key}`}
                            hidden={Boolean(collapsedGroups[group.key])}
                            className={`divide-y divide-copper/15 ${
                                collapsedGroups[group.key] ? "hidden" : ""
                            }`}
                        >
                            {group.clubs.map((club) => {
                                const draft = draftFor(club);
                                const dirty = isDirty(club, draft);
                                const disabled = pendingId !== null;
                                return (
                                    <li
                                        key={club.id}
                                        className="grid gap-4 px-4 py-4 xl:grid-cols-[minmax(280px,1fr)_minmax(260px,380px)_minmax(320px,460px)]"
                                    >
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <Link
                                                    href={`/admin/clubs/${club.id}`}
                                                    className="font-gilroy-bold text-h3 text-cedar hover:underline"
                                                >
                                                    {club.name}
                                                </Link>
                                                <span
                                                    className={`rounded-full border px-2 py-1 font-dmSans text-caption font-semibold ${statusBadgeClass(club)}`}
                                                >
                                                    {club.status}
                                                </span>
                                                {!club.visible && (
                                                    <span className="rounded-full border border-gray-500/30 bg-gray-100 px-2 py-1 font-dmSans text-caption font-semibold text-gray-900">
                                                        Hidden
                                                    </span>
                                                )}
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-body text-soft-charcoal">
                                                <span>ID {club.id}</span>
                                                <span>
                                                    {[club.city, club.state]
                                                        .filter(Boolean)
                                                        .join(", ") || "—"}
                                                </span>
                                                <span>{club.clubType}</span>
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-3 font-dmSans text-caption">
                                                <a
                                                    href={club.website}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                >
                                                    Website
                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                </a>
                                                <Link
                                                    href={`/club/${encodeURIComponent(club.name)}`}
                                                    target="_blank"
                                                    className="text-copper-dark hover:underline"
                                                >
                                                    Public page
                                                </Link>
                                            </div>
                                        </div>

                                        <div className="font-dmSans text-body text-soft-charcoal">
                                            <div>
                                                <span className="font-semibold text-cedar">
                                                    Shows scraped:
                                                </span>{" "}
                                                {club.scrapedShowCount.toLocaleString()}
                                            </div>
                                            <div>
                                                <span className="font-semibold text-cedar">
                                                    Stored total:
                                                </span>{" "}
                                                {club.totalShows.toLocaleString()}
                                            </div>
                                            <div>
                                                <span className="font-semibold text-cedar">
                                                    Latest scrape:
                                                </span>{" "}
                                                {formatDate(
                                                    club.latestScrapeAt,
                                                )}
                                                {club.latestScrapeBy
                                                    ? ` by ${club.latestScrapeBy}`
                                                    : ""}
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {club.scrapingSources.length ===
                                                0 ? (
                                                    <span className="rounded-md border border-amber-700/30 bg-amber-50 px-2 py-1 text-caption font-semibold text-amber-900">
                                                        No scraping source
                                                    </span>
                                                ) : (
                                                    club.scrapingSources.map(
                                                        (source) => (
                                                            <span
                                                                key={source.id}
                                                                className={`rounded-md border px-2 py-1 text-caption font-semibold ${
                                                                    source.enabled
                                                                        ? "border-green-700/30 bg-green-50 text-green-900"
                                                                        : "border-gray-500/30 bg-gray-100 text-gray-900"
                                                                }`}
                                                            >
                                                                {
                                                                    source.priority
                                                                }
                                                                :{" "}
                                                                {
                                                                    source.platform
                                                                }{" "}
                                                                ·{" "}
                                                                {
                                                                    source.scraperKey
                                                                }
                                                            </span>
                                                        ),
                                                    )
                                                )}
                                            </div>
                                        </div>

                                        <div className="grid gap-3 md:grid-cols-2">
                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                                Status
                                                <select
                                                    value={draft.status}
                                                    onChange={(event) =>
                                                        updateDraft(club, {
                                                            status: event.target
                                                                .value,
                                                        })
                                                    }
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                >
                                                    {CLUB_STATUS_OPTIONS.map(
                                                        (option) => (
                                                            <option
                                                                key={option}
                                                                value={option}
                                                            >
                                                                {option}
                                                            </option>
                                                        ),
                                                    )}
                                                </select>
                                            </label>
                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                                Visibility
                                                <select
                                                    value={
                                                        draft.visible
                                                            ? "visible"
                                                            : "hidden"
                                                    }
                                                    onChange={(event) =>
                                                        updateDraft(club, {
                                                            visible:
                                                                event.target
                                                                    .value ===
                                                                "visible",
                                                        })
                                                    }
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                >
                                                    <option value="visible">
                                                        visible
                                                    </option>
                                                    <option value="hidden">
                                                        hidden
                                                    </option>
                                                </select>
                                            </label>
                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                                Type
                                                <select
                                                    value={draft.clubType}
                                                    onChange={(event) =>
                                                        updateDraft(club, {
                                                            clubType:
                                                                event.target
                                                                    .value,
                                                        })
                                                    }
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                >
                                                    {CLUB_TYPE_OPTIONS.map(
                                                        (option) => (
                                                            <option
                                                                key={option}
                                                                value={option}
                                                            >
                                                                {option}
                                                            </option>
                                                        ),
                                                    )}
                                                </select>
                                            </label>
                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                                Closed date
                                                <input
                                                    type="date"
                                                    value={draft.closedAt}
                                                    onChange={(event) =>
                                                        updateDraft(club, {
                                                            closedAt:
                                                                event.target
                                                                    .value,
                                                        })
                                                    }
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>
                                            <div className="md:col-span-2">
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    className="gap-2 border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                    disabled={
                                                        disabled ||
                                                        !dirty ||
                                                        pendingId === club.id
                                                    }
                                                    onClick={() =>
                                                        void saveClub(club)
                                                    }
                                                >
                                                    <Save className="h-4 w-4" />
                                                    Save status override
                                                </Button>
                                            </div>
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    </section>
                ))}
            </div>
        </div>
    );
}
