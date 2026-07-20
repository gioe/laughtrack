"use client";

import type { AdminClubListItem } from "@/lib/admin/clubManagement";
import { CLUB_TYPE_OPTIONS } from "@/lib/admin/clubTaxonomy";
import { Button } from "@/ui/components/ui/button";
import { ExternalLink, Save, Trash2, Upload, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
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
        return "border-gray-500/30 bg-gray-100 text-gray-900";
    }
    return "border-green-700/30 bg-green-50 text-green-900";
}

function currentIconUrl(club: AdminClubListItem) {
    return club.activeImageAsset?.iconUrl ?? club.iconUrl;
}

function StagedPreview({
    file,
    alt,
    className,
}: {
    file: File;
    alt: string;
    className: string;
}) {
    const [src, setSrc] = useState<string>("");

    useEffect(() => {
        const url = URL.createObjectURL(file);
        setSrc(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    if (!src) return null;
    return <img src={src} alt={alt} className={className} />;
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
                        className="font-urbanist-bold text-h3 text-cedar hover:underline"
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
                            Blocked
                        </span>
                    )}
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-body text-soft-charcoal">
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
                <div className="mt-3 rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                    <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                        Display name
                    </label>
                    <div className="mt-1 flex items-center gap-2">
                        <input
                            aria-label="Club name"
                            type="text"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            className="min-w-0 flex-1 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                        />
                        <Button
                            type="button"
                            variant="outline"
                            className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
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
                                        : "border-gray-500/30 bg-gray-100 text-gray-900"
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
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Status
                    <select
                        value={draft.status}
                        onChange={(event) =>
                            patchDraft({ status: event.target.value })
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {CLUB_STATUS_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Visibility
                    <select
                        value={draft.visible ? "visible" : "blocked"}
                        onChange={(event) =>
                            patchDraft({
                                visible: event.target.value === "visible",
                            })
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        <option value="visible">visible</option>
                        <option value="blocked">blocked</option>
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Type
                    <select
                        value={draft.clubType}
                        onChange={(event) =>
                            patchDraft({ clubType: event.target.value })
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {CLUB_TYPE_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Closed date
                    <input
                        type="date"
                        value={draft.closedAt}
                        onChange={(event) =>
                            patchDraft({ closedAt: event.target.value })
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    />
                </label>
                <div className="md:col-span-2">
                    <Button
                        type="button"
                        variant="outline"
                        className="gap-2 border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                        disabled={disabled || !statusDirty || pending}
                        onClick={() => void saveStatus()}
                    >
                        <Save className="h-4 w-4" />
                        Save status override
                    </Button>
                </div>
                <div className="space-y-3 rounded-md border border-copper/20 bg-white/80 p-3 md:col-span-2">
                    <div className="flex items-center justify-between gap-2">
                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                            Current image
                        </div>
                        {club.hasImage ? (
                            <a
                                href={currentIconUrl(club)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-copper-dark hover:underline"
                            >
                                Open
                                <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                        ) : null}
                    </div>
                    {club.hasImage ? (
                        <img
                            src={currentIconUrl(club)}
                            alt={`${club.name} current thumbnail image`}
                            className="h-20 w-20 rounded-md border border-copper/20 object-contain"
                        />
                    ) : image.iconFile ? null : (
                        <div className="flex h-20 w-20 items-center justify-center rounded-md border border-dashed border-soft-charcoal/30 bg-gray-50 font-dmSans text-caption text-soft-charcoal">
                            Empty
                        </div>
                    )}
                    <div className="grid gap-1">
                        <label
                            htmlFor={`club-icon-url-${club.id}`}
                            className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal"
                        >
                            Thumbnail image URL
                        </label>
                        <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                            <input
                                id={`club-icon-url-${club.id}`}
                                aria-label="Club thumbnail image URL"
                                type="url"
                                value={image.icon}
                                onChange={(event) =>
                                    patchImage({
                                        icon: event.target.value,
                                        iconFile: null,
                                    })
                                }
                                placeholder="https://example.com/club-logo.png"
                                className="w-full min-w-0 flex-1 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                            />
                            <Button
                                type="button"
                                variant="outline"
                                aria-label="Save club thumbnail URL"
                                className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                disabled={
                                    disabled ||
                                    pending ||
                                    !image.icon.trim() ||
                                    image.icon.trim() === currentIconUrl(club)
                                }
                                onClick={() => void publishImage()}
                            >
                                <Save className="h-4 w-4" />
                                Save URL
                            </Button>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                        <input
                            id={`club-icon-file-${club.id}`}
                            aria-label="Upload club thumbnail file"
                            type="file"
                            accept="image/jpeg,image/png,image/webp,image/avif,image/gif"
                            className="sr-only"
                            onChange={async (event) => {
                                const file = event.target.files?.[0] ?? null;
                                event.target.value = "";
                                if (!file) return;
                                await stageImage(file);
                            }}
                        />
                        <Button
                            type="button"
                            variant="outline"
                            className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                            disabled={disabled || pending}
                            onClick={() => {
                                const input = document.getElementById(
                                    `club-icon-file-${club.id}`,
                                ) as HTMLInputElement | null;
                                input?.click();
                            }}
                        >
                            <Upload className="h-4 w-4" />
                            Choose thumbnail file
                        </Button>
                        <span className="font-dmSans text-caption normal-case tracking-normal text-soft-charcoal">
                            1:1 square, at least 600x600
                        </span>
                    </div>
                    {image.iconFile ? (
                        <div className="inline-flex max-w-full flex-wrap items-center gap-3 rounded-md border border-copper/30 bg-coconut-cream/30 p-3">
                            <StagedPreview
                                file={image.iconFile}
                                alt={`${club.name} pending thumbnail`}
                                className="h-16 w-16 shrink-0 rounded-md border border-copper/30 object-contain"
                            />
                            <div className="grid min-w-[220px] flex-1 gap-2">
                                <div>
                                    <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Pending thumbnail
                                    </div>
                                    <div className="font-dmSans text-caption text-soft-charcoal">
                                        Publish the staged file or discard it
                                        before choosing another.
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <Button
                                        type="button"
                                        className="gap-2 bg-copper-dark text-white hover:bg-cedar disabled:bg-gray-300 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={disabled || pending}
                                        onClick={() => void publishImage()}
                                    >
                                        <Upload className="h-4 w-4" />
                                        Publish to Bunny
                                    </Button>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="gap-2 border-soft-charcoal/40 bg-white text-cedar hover:bg-gray-50"
                                        disabled={disabled || pending}
                                        onClick={discardStagedFile}
                                    >
                                        <X className="h-4 w-4" />
                                        Discard
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ) : null}
                    {imageStatus ? (
                        <p
                            className={
                                imageStatus.kind === "error"
                                    ? "rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-caption font-semibold text-red-900"
                                    : "rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-caption font-semibold text-green-900"
                            }
                        >
                            {imageStatus.message}
                        </p>
                    ) : null}
                    {club.hasImage ? (
                        <Button
                            type="button"
                            variant="outline"
                            className="gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                            disabled={disabled || pending}
                            onClick={() => void removeImage()}
                        >
                            <Trash2 className="h-4 w-4" />
                            Remove thumbnail
                        </Button>
                    ) : null}
                    <Button
                        type="button"
                        variant="outline"
                        className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                        disabled={disabled || pending || !imageDirty}
                        onClick={() => void publishImage()}
                    >
                        <Upload className="h-4 w-4" />
                        Upload changed image
                    </Button>
                </div>
            </div>
        </li>
    );
}
