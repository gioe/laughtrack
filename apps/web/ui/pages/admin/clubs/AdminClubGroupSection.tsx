"use client";

import type {
    AdminClubGroup,
    AdminClubListItem,
} from "@/lib/admin/clubManagement";
import { CLUB_TYPE_OPTIONS } from "@/lib/admin/clubTaxonomy";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { AdminClubRow } from "./AdminClubRow";

export type ClubGroupView = "chain" | "scraper";

export type DisplayClubGroup = AdminClubGroup & {
    title: string;
    website: string | null;
    grouping: ClubGroupView;
};

export type ClubGroupControls = {
    query: string;
    sort: string;
    status: string;
    visibility: string;
    clubType: string;
};

export type AdminClubGroupSectionProps = {
    group: DisplayClubGroup;
    clubs: AdminClubListItem[];
    collapsed: boolean;
    controls: ClubGroupControls;
    onToggle: () => void;
    onControlsChange: (patch: Partial<ClubGroupControls>) => void;
};

const CLUB_STATUS_OPTIONS = ["active", "closed", "hiatus", "not_open_yet"];

export function AdminClubGroupSection({
    group,
    clubs,
    collapsed,
    controls,
    onToggle,
    onControlsChange,
}: AdminClubGroupSectionProps) {
    const groupName = group.title;
    const panelId = `club-chain-${group.key}`;

    return (
        <section className="overflow-hidden rounded-md border border-copper/20 bg-surface-elevated">
            <header className="border-b border-copper/20 bg-cedar px-4 py-3 text-white">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <button
                        type="button"
                        aria-expanded={!collapsed}
                        aria-controls={panelId}
                        onClick={onToggle}
                        className="flex min-w-0 items-start gap-3 text-left"
                    >
                        <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/10">
                            {collapsed ? (
                                <ChevronRight className="h-4 w-4" />
                            ) : (
                                <ChevronDown className="h-4 w-4" />
                            )}
                        </span>
                        <span className="min-w-0">
                            <span className="block font-urbanist-bold text-h3 leading-tight">
                                {groupName}
                            </span>
                            <span className="mt-1 block font-dmSans text-caption text-white/85">
                                {group.clubs.length} clubs in this{" "}
                                {group.grouping} group ·{" "}
                                {group.totals.visibleCount} visible ·{" "}
                                {group.totals.activeCount} active ·{" "}
                                {group.totals.scrapedShowCount.toLocaleString()}{" "}
                                scraped shows
                            </span>
                        </span>
                    </button>
                    <div className="flex items-center gap-3 pl-10 md:pl-0">
                        {group.website && (
                            <a
                                href={group.website}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-white hover:underline"
                            >
                                Group site
                                <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                        )}
                    </div>
                </div>
            </header>

            <div
                id={panelId}
                hidden={collapsed}
                className={`${collapsed ? "hidden" : ""}`}
            >
                <div className="border-b border-copper/20 bg-surface-muted/70 px-4 py-3">
                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_150px_150px_150px] md:items-end">
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                            Search within {groupName}
                            <input
                                aria-label={`Search within ${groupName}`}
                                type="search"
                                value={controls.query}
                                onChange={(event) =>
                                    onControlsChange({
                                        query: event.target.value,
                                    })
                                }
                                className="rounded-md border border-input bg-background px-3 py-2 font-dmSans text-body text-foreground outline-none placeholder:text-muted-foreground focus:border-copper focus:ring-2 focus:ring-copper/30"
                                placeholder="Club, city, status, scraper"
                            />
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                            Sort clubs
                            <select
                                aria-label={`Sort ${groupName} clubs`}
                                value={controls.sort}
                                onChange={(event) =>
                                    onControlsChange({
                                        sort: event.target.value,
                                    })
                                }
                                className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="name-asc">Name A-Z</option>
                                <option value="name-desc">Name Z-A</option>
                                <option value="shows-desc">
                                    Scraped shows high-low
                                </option>
                                <option value="shows-asc">
                                    Scraped shows low-high
                                </option>
                                <option value="latest-desc">
                                    Latest scrape newest
                                </option>
                                <option value="latest-asc">
                                    Latest scrape oldest
                                </option>
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                            Status filter
                            <select
                                aria-label={`Filter ${groupName} clubs by status`}
                                value={controls.status}
                                onChange={(event) =>
                                    onControlsChange({
                                        status: event.target.value,
                                    })
                                }
                                className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                {CLUB_STATUS_OPTIONS.map((option) => (
                                    <option key={option} value={option}>
                                        {option}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                            Visibility filter
                            <select
                                aria-label={`Filter ${groupName} clubs by visibility`}
                                value={controls.visibility}
                                onChange={(event) =>
                                    onControlsChange({
                                        visibility: event.target.value,
                                    })
                                }
                                className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                <option value="visible">Visible</option>
                                <option value="blocked">Blocked</option>
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                            Type filter
                            <select
                                aria-label={`Filter ${groupName} clubs by type`}
                                value={controls.clubType}
                                onChange={(event) =>
                                    onControlsChange({
                                        clubType: event.target.value,
                                    })
                                }
                                className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                {CLUB_TYPE_OPTIONS.map((option) => (
                                    <option key={option} value={option}>
                                        {option}
                                    </option>
                                ))}
                            </select>
                        </label>
                    </div>
                    <div className="mt-2 font-dmSans text-caption font-semibold text-muted-foreground">
                        {clubs.length.toLocaleString()} of{" "}
                        {group.clubs.length.toLocaleString()} clubs shown
                    </div>
                </div>
                <ul className="divide-y divide-copper/15">
                    {clubs.map((club) => (
                        <AdminClubRow key={club.id} club={club} />
                    ))}
                </ul>
            </div>
        </section>
    );
}
