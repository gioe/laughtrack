"use client";

import type { AdminClubListItem } from "@/lib/admin/clubManagement";
import { CLUB_TYPE_OPTIONS } from "@/lib/admin/clubTaxonomy";
import { Button } from "@/ui/components/ui/button";
import { ExternalLink, Save, Upload } from "lucide-react";
import Link from "next/link";
import { AdminImageEditor } from "../shared/AdminImageEditor";
import { useAdminClubRowController } from "./AdminClubRowController";

const CLUB_STATUS_OPTIONS = ["active", "closed", "hiatus", "not_open_yet"];

function formatDate(iso: string | null) {
    if (!iso) return "Never";
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function normalizedClubName(name: string) {
    return name.trim().replace(/\s+/g, " ");
}

function statusBadgeClass(club: AdminClubListItem) {
    if (club.status === "closed") {
        return "border-red-700/30 bg-red-50 text-red-900";
    }
    if (club.status === "hiatus") {
        return "border-amber-700/30 bg-amber-50 text-amber-900";
    }
    if (club.status === "not_open_yet") {
        return "border-sky-700/30 bg-sky-50 text-sky-900";
    }
    if (!club.visible) {
        return "border-strong bg-surface-muted text-foreground";
    }
    return "border-green-700/30 bg-green-50 text-green-900";
}

function currentIconUrl(club: AdminClubListItem) {
    return club.activeImageAsset?.iconUrl ?? club.iconUrl;
}

export function AdminClubRow({ club }: { club: AdminClubListItem }) {
    const {
        draft,
        name,
        image,
        imageStatus,
        statusDirty,
        nameDirty,
        imageDirty,
        disabled,
        pending,
        setName,
        patchDraft,
        patchImage,
        saveName,
        saveStatus,
        stageImage,
        discardStagedFile,
        publishImage,
        removeImage,
    } = useAdminClubRowController(club);

    return (
        <li className="grid gap-4 px-4 py-4 xl:grid-cols-[minmax(260px,0.95fr)_minmax(240px,320px)_minmax(300px,420px)]">
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <Link
                        href={`/admin/clubs/${club.id}`}
                        className="font-urbanist-bold text-h3 text-foreground hover:underline"
                    >
                        {club.name}
                    </Link>
                    <span
                        className={`rounded-full border px-2 py-1 font-dmSans text-caption font-semibold ${statusBadgeClass(club)}`}
                    >
                        {club.status}
                    </span>
                    {!club.visible && (
                        <span className="rounded-full border border-strong bg-surface-muted px-2 py-1 font-dmSans text-caption font-semibold text-foreground">
                            Blocked
                        </span>
                    )}
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-body text-muted-foreground">
                    <span>ID {club.id}</span>
                    <span>
                        {[club.city, club.state].filter(Boolean).join(", ") ||
                            "—"}
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
                <div className="mt-3 rounded-md border border-copper/20 bg-surface-muted/35 p-3">
                    <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-muted-foreground">
                        Display name
                    </label>
                    <div className="mt-1 flex items-center gap-2">
                        <input
                            aria-label="Club name"
                            type="text"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 font-dmSans text-body normal-case tracking-normal text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                        />
                        <Button
                            type="button"
                            variant="outline"
                            className="shrink-0 gap-2 border-copper/40 bg-surface-elevated text-foreground hover:bg-copper/10 disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                            disabled={
                                disabled ||
                                pending ||
                                !nameDirty ||
                                !normalizedClubName(name)
                            }
                            onClick={() => void saveName()}
                        >
                            <Save className="h-4 w-4" />
                            Save name
                        </Button>
                    </div>
                </div>
            </div>

            <div className="font-dmSans text-body text-muted-foreground">
                <div>
                    <span className="font-semibold text-foreground">
                        Shows scraped:
                    </span>{" "}
                    {club.scrapedShowCount.toLocaleString()}
                </div>
                <div>
                    <span className="font-semibold text-foreground">
                        Stored total:
                    </span>{" "}
                    {club.totalShows.toLocaleString()}
                </div>
                <div>
                    <span className="font-semibold text-foreground">
                        Latest scrape:
                    </span>{" "}
                    {formatDate(club.latestScrapeAt)}
                    {club.latestScrapeBy ? ` by ${club.latestScrapeBy}` : ""}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                    {club.scrapingSources.length === 0 ? (
                        <span className="rounded-md border border-amber-700/30 bg-amber-50 px-2 py-1 text-caption font-semibold text-amber-900">
                            No scraping source
                        </span>
                    ) : (
                        club.scrapingSources.map((source) => (
                            <span
                                key={source.id}
                                className={`rounded-md border px-2 py-1 text-caption font-semibold ${
                                    source.enabled
                                        ? "border-green-700/30 bg-green-50 text-green-900"
                                        : "border-strong bg-surface-muted text-foreground"
                                }`}
                            >
                                {source.priority}: {source.platform} ·{" "}
                                {source.scraperKey}
                            </span>
                        ))
                    )}
                </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                    Status
                    <select
                        value={draft.status}
                        onChange={(event) =>
                            patchDraft({ status: event.target.value })
                        }
                        className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {CLUB_STATUS_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                    Visibility
                    <select
                        value={draft.visible ? "visible" : "blocked"}
                        onChange={(event) =>
                            patchDraft({
                                visible: event.target.value === "visible",
                            })
                        }
                        className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        <option value="visible">visible</option>
                        <option value="blocked">blocked</option>
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                    Type
                    <select
                        value={draft.clubType}
                        onChange={(event) =>
                            patchDraft({ clubType: event.target.value })
                        }
                        className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {CLUB_TYPE_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                    Closed date
                    <input
                        type="date"
                        value={draft.closedAt}
                        onChange={(event) =>
                            patchDraft({ closedAt: event.target.value })
                        }
                        className="rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    />
                </label>
                <div className="md:col-span-2">
                    <Button
                        type="button"
                        variant="outline"
                        className="gap-2 border-copper-dark bg-surface-elevated text-copper-dark disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                        disabled={disabled || !statusDirty || pending}
                        onClick={() => void saveStatus()}
                    >
                        <Save className="h-4 w-4" />
                        Save status override
                    </Button>
                </div>
                <div className="md:col-span-2">
                    <AdminImageEditor
                        id={`club-icon-${club.id}`}
                        title="Current image"
                        currentImage={
                            club.hasImage
                                ? {
                                      url: currentIconUrl(club),
                                      alt: `${club.name} current thumbnail image`,
                                      className:
                                          "h-20 w-20 rounded-md border border-copper/20 object-contain",
                                  }
                                : undefined
                        }
                        emptyClassName="flex h-20 w-20 items-center justify-center rounded-md border border-dashed border-strong bg-surface-muted font-dmSans text-caption text-muted-foreground"
                        urlInput={{
                            label: "Thumbnail image URL",
                            ariaLabel: "Club thumbnail image URL",
                            value: image.icon,
                            placeholder: "https://example.com/club-logo.png",
                            saveAriaLabel: "Save club thumbnail URL",
                            canSave: Boolean(
                                image.icon.trim() &&
                                    image.icon.trim() !== currentIconUrl(club),
                            ),
                            onChange: (value) =>
                                patchImage({ icon: value, iconFile: null }),
                            onSave: publishImage,
                        }}
                        fileInput={{
                            ariaLabel: "Upload club thumbnail file",
                            chooseLabel: "Choose thumbnail file",
                            guidance: "1:1 square, at least 600x600",
                            stagedFile: image.iconFile,
                            pendingLabel: "Pending thumbnail",
                            pendingAlt: `${club.name} pending thumbnail`,
                            previewClassName:
                                "h-16 w-16 shrink-0 rounded-md border border-copper/30 object-contain",
                            onSelect: stageImage,
                            onPublish: publishImage,
                            onDiscard: discardStagedFile,
                        }}
                        status={imageStatus}
                        disabled={disabled || pending}
                        remove={{
                            visible: club.hasImage,
                            label: "Remove thumbnail",
                            onRemove: removeImage,
                        }}
                    />
                    <div className="mt-3">
                        <Button
                            type="button"
                            variant="outline"
                            className="gap-2 border-copper/40 bg-surface-elevated text-foreground hover:bg-copper/10 disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                            disabled={disabled || pending || !imageDirty}
                            onClick={() => void publishImage()}
                        >
                            <Upload className="h-4 w-4" />
                            Upload changed image
                        </Button>
                    </div>
                </div>
            </div>
        </li>
    );
}
