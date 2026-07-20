"use client";

import { validateComedianImageFile } from "@/lib/admin/comedianImageClientValidation";
import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { Button } from "@/ui/components/ui/button";
import { adminRequest } from "../shared/adminRequest";
import { AdminImageEditor } from "../shared/AdminImageEditor";
import {
    ChevronDown,
    ChevronRight,
    ExternalLink,
    Save,
    Trash2,
    Upload,
    X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition, type ReactNode } from "react";
import { BlockedComedianRow } from "./BlockedComedianRow";
import { ComedianImageSection } from "./ComedianImageSection";
import { ComedianPodcastSection } from "./ComedianPodcastSection";
import { ComedianProfileSection } from "./ComedianProfileSection";
import { ComedianRelationshipSection } from "./ComedianRelationshipSection";
import { ComedianSocialSection } from "./ComedianSocialSection";

type Props = {
    row: AdminComedianListItem;
    allRows: AdminComedianListItem[];
    children: AdminComedianListItem[];
    onRowChange: (row: AdminComedianListItem) => void;
    globallyDisabled: boolean;
    onPendingChange: (rowId: number, pending: boolean) => void;
    onStatusChange: (status: Status) => void;
};

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type ProfileEdit = {
    website: string;
    websiteScrapingUrl: string;
    instagramAccount: string;
    tiktokAccount: string;
    youtubeAccount: string;
    youtubeChannelId: string;
    linktree: string;
};

type ProfileField = keyof ProfileEdit;
type YouTubeWebSubComedianFlag =
    | "youtubeLiveFeedEnabled"
    | "youtubeLiveNotificationsEnabled";

type ManualImageUrls = {
    headshot: string;
    hero: string;
    headshotFile: File | null;
    heroFile: File | null;
};

type AttributedPodcast = AdminComedianListItem["attributedPodcasts"][number];
type PodcastCandidateReview =
    AdminComedianListItem["podcastCandidateReviews"][number];

const DEFAULT_BLOCK_REASON = "not a comic";

function acceptedAttributedPodcasts(row: AdminComedianListItem) {
    return row.attributedPodcasts.filter(
        (podcast) => podcast.reviewStatus === "accepted",
    );
}

function formatDate(iso: string | null) {
    if (!iso) return null;
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function formatDimensions(width: number | null, height: number | null) {
    return width && height ? `${width}x${height}` : "Unknown size";
}

function formatPercent(value: number) {
    return `${Math.round(value * 100)}%`;
}

function nameComedianImageUrl(row: AdminComedianListItem) {
    return row.nameImageUrl;
}

function currentAvatarUrl(row: AdminComedianListItem) {
    if (row.activeImageAsset) return row.activeImageAsset.avatarUrl ?? "";
    return row.hasImage ? nameComedianImageUrl(row) : "";
}

function currentHeroUrl(row: AdminComedianListItem) {
    if (row.activeImageAsset) return row.activeImageAsset.heroUrl ?? "";
    return row.hasImage ? nameComedianImageUrl(row) : "";
}

function compareByName(a: AdminComedianListItem, b: AdminComedianListItem) {
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

function ComedianRowHeadshot({ row }: { row: AdminComedianListItem }) {
    const src = currentAvatarUrl(row);
    if (!src) return null;
    return (
        <img
            src={src}
            alt={`${row.name} headshot`}
            className="h-11 w-11 shrink-0 rounded-md border border-copper/25 object-cover"
        />
    );
}

function SummaryPill({
    label,
    value,
    tone = "neutral",
}: {
    label: string;
    value: ReactNode;
    tone?: "neutral" | "good" | "warn";
}) {
    const toneClass =
        tone === "good"
            ? "border-green-700/25 bg-green-50 text-green-950"
            : tone === "warn"
              ? "border-red-700/25 bg-red-50 text-red-950"
              : "border-copper/20 bg-white text-cedar";
    return (
        <span
            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-dmSans text-caption ${toneClass}`}
        >
            <span className="font-semibold uppercase text-soft-charcoal">
                {label}
            </span>
            <span className="font-semibold">{value}</span>
        </span>
    );
}

export function AdminComedianRow({
    row,
    allRows,
    children,
    onRowChange,
    globallyDisabled,
    onPendingChange,
    onStatusChange,
}: Props) {
    const router = useRouter();
    const [openChildrenSections, setOpenChildrenSections] = useState<
        Set<number>
    >(() => new Set<number>());
    const [parentSearches, setParentSearches] = useState<
        Record<number, string>
    >({});
    const [selectedParents, setSelectedParents] = useState<
        Record<number, AdminComedianListItem["parent"]>
    >({});
    const [nameEdits, setNameEdits] = useState<Record<number, string>>({});
    const [profileEdits, setProfileEdits] = useState<
        Record<number, ProfileEdit>
    >({});
    // Comedian rows default to collapsed; the operator expands the ones they
    // want to work on. (Previously every row was seeded open.)
    const [openComedianRows, setOpenComedianRows] = useState<Set<number>>(
        () => new Set<number>(),
    );
    const [openImageSections, setOpenImageSections] = useState<Set<number>>(
        () => new Set<number>(),
    );
    const [openSocialSections, setOpenSocialSections] = useState<Set<number>>(
        () => new Set<number>(),
    );
    const [openPodcastSections, setOpenPodcastSections] = useState<Set<number>>(
        () => new Set<number>(),
    );
    const [manualImageUrls, setManualImageUrls] = useState<
        Record<number, ManualImageUrls>
    >({});
    const [podcastFeedEdits, setPodcastFeedEdits] = useState<
        Record<string, string>
    >({});
    const [manualPodcastFeedUrls, setManualPodcastFeedUrls] = useState<
        Record<number, string>
    >({});
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [savingWebSubKey, setSavingWebSubKey] = useState<string | null>(null);
    const [imageStatusByRow, setImageStatusByRow] = useState<
        Record<number, { kind: "ok" | "error"; message: string }>
    >({});
    const [isPending, startTransition] = useTransition();
    const setStatus = onStatusChange;

    useEffect(() => {
        onPendingChange(
            row.id,
            pendingId !== null || savingWebSubKey !== null || isPending,
        );
        return () => onPendingChange(row.id, false);
    }, [isPending, onPendingChange, pendingId, row.id, savingWebSubKey]);

    function parentValue(row: AdminComedianListItem) {
        return Object.hasOwn(selectedParents, row.id)
            ? selectedParents[row.id]
            : row.parent;
    }

    function isParentDirty(row: AdminComedianListItem) {
        if (!Object.hasOwn(selectedParents, row.id)) return false;
        return selectedParents[row.id]?.id !== row.parent?.id;
    }

    function nameValue(row: AdminComedianListItem) {
        return Object.hasOwn(nameEdits, row.id) ? nameEdits[row.id] : row.name;
    }

    function normalizedAdminName(name: string) {
        return name.trim().replace(/\s+/g, " ");
    }

    function normalizedUrl(value: string) {
        return value.trim() || null;
    }

    function isNameDirty(row: AdminComedianListItem) {
        return normalizedAdminName(nameValue(row)) !== row.name;
    }

    function rowDefaultFor(
        row: AdminComedianListItem,
        field: ProfileField,
    ): string {
        return row[field] ?? "";
    }

    function profileFieldValue(
        row: AdminComedianListItem,
        field: ProfileField,
    ) {
        return profileEdits[row.id]?.[field] ?? rowDefaultFor(row, field);
    }

    function snapshotProfileEdit(row: AdminComedianListItem): ProfileEdit {
        return {
            website: profileFieldValue(row, "website"),
            websiteScrapingUrl: profileFieldValue(row, "websiteScrapingUrl"),
            instagramAccount: profileFieldValue(row, "instagramAccount"),
            tiktokAccount: profileFieldValue(row, "tiktokAccount"),
            youtubeAccount: profileFieldValue(row, "youtubeAccount"),
            youtubeChannelId: profileFieldValue(row, "youtubeChannelId"),
            linktree: profileFieldValue(row, "linktree"),
        };
    }

    const PROFILE_FIELDS: ProfileField[] = [
        "website",
        "websiteScrapingUrl",
        "instagramAccount",
        "tiktokAccount",
        "youtubeAccount",
        "youtubeChannelId",
        "linktree",
    ];

    function isProfileDirty(row: AdminComedianListItem) {
        return PROFILE_FIELDS.some(
            (field) =>
                normalizedUrl(profileFieldValue(row, field)) !==
                (row[field] ?? null),
        );
    }

    function isRecordDirty(row: AdminComedianListItem) {
        return isNameDirty(row) || isProfileDirty(row);
    }

    function updateProfileEdit(
        row: AdminComedianListItem,
        patch: Partial<ProfileEdit>,
    ) {
        setProfileEdits((current) => ({
            ...current,
            [row.id]: { ...snapshotProfileEdit(row), ...patch },
        }));
    }

    function toggleComedianRow(rowId: number) {
        setOpenComedianRows((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
    }

    function toggleChildrenSection(rowId: number) {
        setOpenChildrenSections((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
    }

    function toggleImageSection(rowId: number) {
        setOpenImageSections((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
    }

    function toggleSocialSection(rowId: number) {
        setOpenSocialSections((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
    }

    function togglePodcastSection(rowId: number) {
        setOpenPodcastSections((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
    }

    function parentCandidates(row: AdminComedianListItem) {
        const search = parentSearches[row.id]?.trim().toLowerCase() ?? "";
        if (!search) return [];
        return allRows
            .filter((candidate) => {
                return (
                    candidate.id !== row.id &&
                    candidate.name.toLowerCase().includes(search)
                );
            })
            .sort(compareByName)
            .slice(0, 8);
    }

    async function saveParent(
        row: AdminComedianListItem,
        parentOverride?: AdminComedianListItem["parent"],
    ) {
        const parent =
            parentOverride === undefined ? parentValue(row) : parentOverride;
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { comedian: AdminComedianListItem };
        try {
            body = await adminRequest<{ comedian: AdminComedianListItem }>(
                "/api/admin/comedians",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action: "set-parent",
                        comedianId: row.id,
                        parentComedianId: parent?.id ?? null,
                    }),
                },
            );
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
        onRowChange(body.comedian);
        setSelectedParents((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setParentSearches((current) => ({ ...current, [row.id]: "" }));
        setStatus({ kind: "ok", message: `${row.name} relationship saved.` });
        startTransition(() => router.refresh());
    }

    async function saveComedianRecord(row: AdminComedianListItem) {
        const name = normalizedAdminName(nameValue(row));
        if (!name || !isRecordDirty(row)) return;

        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { comedian: AdminComedianListItem };
        try {
            body = await adminRequest<{ comedian: AdminComedianListItem }>(
                "/api/admin/comedians",
                {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        comedianId: row.id,
                        name,
                        website: normalizedUrl(
                            profileFieldValue(row, "website"),
                        ),
                        websiteScrapingUrl: normalizedUrl(
                            profileFieldValue(row, "websiteScrapingUrl"),
                        ),
                        instagramAccount: normalizedUrl(
                            profileFieldValue(row, "instagramAccount"),
                        ),
                        tiktokAccount: normalizedUrl(
                            profileFieldValue(row, "tiktokAccount"),
                        ),
                        youtubeAccount: normalizedUrl(
                            profileFieldValue(row, "youtubeAccount"),
                        ),
                        youtubeChannelId: normalizedUrl(
                            profileFieldValue(row, "youtubeChannelId"),
                        ),
                        linktree: normalizedUrl(
                            profileFieldValue(row, "linktree"),
                        ),
                    }),
                },
            );
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
        onRowChange(body.comedian);
        setNameEdits((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setProfileEdits((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${row.name} record saved.` });
        startTransition(() => router.refresh());
    }

    async function blockComedian(row: AdminComedianListItem) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { comedian: AdminComedianListItem };
        try {
            body = await adminRequest<{ comedian: AdminComedianListItem }>(
                "/api/admin/comedians",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action: "blocklist-add",
                        comedianId: row.id,
                        reason: DEFAULT_BLOCK_REASON,
                    }),
                },
            );
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
        onRowChange(body.comedian);
        setStatus({ kind: "ok", message: `${row.name} added to blocklist.` });
        startTransition(() => router.refresh());
    }

    async function unblockComedian(row: AdminComedianListItem) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { comedian: AdminComedianListItem };
        try {
            body = await adminRequest<{ comedian: AdminComedianListItem }>(
                "/api/admin/comedians",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action: "blocklist-remove",
                        comedianId: row.id,
                    }),
                },
            );
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
        onRowChange(body.comedian);
        setStatus({
            kind: "ok",
            message: `${row.name} removed from blocklist.`,
        });
        startTransition(() => router.refresh());
    }

    async function saveYouTubeWebSubFlag(
        row: AdminComedianListItem,
        flag: YouTubeWebSubComedianFlag,
        value: boolean,
    ) {
        const key = `${row.uuid}:${flag}`;
        setSavingWebSubKey(key);
        setStatus({ kind: "idle" });

        try {
            await adminRequest(
                `/api/admin/youtube-websub/comedians/${encodeURIComponent(row.uuid)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ [flag]: value }),
                },
            );
        } catch (error) {
            setSavingWebSubKey(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setSavingWebSubKey(null);
        onRowChange({ ...row, [flag]: value });
        setStatus({
            kind: "ok",
            message: `${row.name} YouTube WebSub flag saved.`,
        });
        startTransition(() => router.refresh());
    }

    async function reviewPodcastCandidate(
        row: AdminComedianListItem,
        review: PodcastCandidateReview,
        action:
            | "podcast-review-accept-host"
            | "podcast-review-reject-host"
            | "podcast-review-block-podcast",
    ) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { comedian: AdminComedianListItem };
        try {
            body = await adminRequest<{ comedian: AdminComedianListItem }>(
                "/api/admin/comedians",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action,
                        comedianId: row.id,
                        candidateReviewId: review.id,
                        ...(action === "podcast-review-block-podcast"
                            ? {
                                  reason: `Blocked from comedian podcast review for ${row.name}`,
                              }
                            : {}),
                    }),
                },
            );
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
        onRowChange(body.comedian);
        const title = review.podcast?.title ?? review.sourcePodcastId;
        setStatus({
            kind: "ok",
            message:
                action === "podcast-review-accept-host"
                    ? `${title} accepted as a host podcast for ${row.name}.`
                    : action === "podcast-review-reject-host"
                      ? `${title} rejected as a host podcast for ${row.name}.`
                      : `${title} blocked from podcast ingestion.`,
        });
        startTransition(() => router.refresh());
    }

    function manualImageUrlValue(row: AdminComedianListItem) {
        return (
            manualImageUrls[row.id] ?? {
                headshot: currentAvatarUrl(row),
                hero: currentHeroUrl(row),
                headshotFile: null,
                heroFile: null,
            }
        );
    }

    function updateManualImageUrls(
        row: AdminComedianListItem,
        patch: Partial<ManualImageUrls>,
    ) {
        setManualImageUrls((current) => ({
            ...current,
            [row.id]: {
                headshot: manualImageUrlValue(row).headshot,
                hero: manualImageUrlValue(row).hero,
                headshotFile: manualImageUrlValue(row).headshotFile,
                heroFile: manualImageUrlValue(row).heroFile,
                ...patch,
            },
        }));
    }

    function imageSlotHasInput(
        row: AdminComedianListItem,
        slot: "headshot" | "hero",
    ) {
        const inputs = manualImageUrlValue(row);
        if (slot === "headshot") {
            return Boolean(
                inputs.headshotFile ||
                    (inputs.headshot.trim() &&
                        inputs.headshot.trim() !== currentAvatarUrl(row)),
            );
        }
        return Boolean(
            inputs.heroFile ||
                (inputs.hero.trim() &&
                    inputs.hero.trim() !== currentHeroUrl(row)),
        );
    }

    async function stageImageFile(
        row: AdminComedianListItem,
        slot: "headshot" | "hero",
        file: File,
    ) {
        const result = await validateComedianImageFile(file, slot);
        if (!result.ok) {
            setStatus({ kind: "error", message: result.reason });
            setImageStatusByRow((current) => ({
                ...current,
                [row.id]: { kind: "error", message: result.reason },
            }));
            return;
        }
        updateManualImageUrls(
            row,
            slot === "headshot" ? { headshotFile: file } : { heroFile: file },
        );
        setStatus({ kind: "idle" });
        setImageStatusByRow((current) => ({
            ...current,
            [row.id]: {
                kind: "ok",
                message: `${slot === "headshot" ? "Headshot" : "Hero"} staged at ${file.name}. Click "Publish to Bunny" to commit, or "Discard" to remove.`,
            },
        }));
    }

    function discardStagedFile(
        row: AdminComedianListItem,
        slot: "headshot" | "hero",
    ) {
        updateManualImageUrls(
            row,
            slot === "headshot" ? { headshotFile: null } : { heroFile: null },
        );
        setImageStatusByRow((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
    }

    function podcastFeedEditKey(
        row: AdminComedianListItem,
        podcast: AttributedPodcast,
    ) {
        return `${row.id}:${podcast.id}`;
    }

    function podcastFeedValue(
        row: AdminComedianListItem,
        podcast: AttributedPodcast,
    ) {
        const key = podcastFeedEditKey(row, podcast);
        return Object.hasOwn(podcastFeedEdits, key)
            ? podcastFeedEdits[key]
            : (podcast.feedUrl ?? "");
    }

    function updatePodcastFeedValue(
        row: AdminComedianListItem,
        podcast: AttributedPodcast,
        value: string,
    ) {
        setPodcastFeedEdits((current) => ({
            ...current,
            [podcastFeedEditKey(row, podcast)]: value,
        }));
    }

    function manualPodcastFeedValue(row: AdminComedianListItem) {
        return manualPodcastFeedUrls[row.id] ?? "";
    }

    function replacePodcastForRow(rowId: number, podcast: AttributedPodcast) {
        const target = allRows.find((candidate) => candidate.id === rowId);
        if (!target) return;
        const found = target.attributedPodcasts.some(
            (currentPodcast) => currentPodcast.id === podcast.id,
        );
        onRowChange({
            ...target,
            attributedPodcasts: found
                ? target.attributedPodcasts.map((currentPodcast) =>
                      currentPodcast.id === podcast.id
                          ? podcast
                          : currentPodcast,
                  )
                : [...target.attributedPodcasts, podcast],
        });
    }

    async function savePodcastFeedUrl(
        row: AdminComedianListItem,
        podcast: AttributedPodcast,
        feedUrl: string | null,
    ) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { podcast: AttributedPodcast };
        try {
            body = await adminRequest<{ podcast: AttributedPodcast }>(
                "/api/admin/comedians/podcasts",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        comedianId: row.id,
                        podcastId: podcast.id,
                        feedUrl,
                    }),
                },
            );
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
        replacePodcastForRow(row.id, body.podcast);
        setPodcastFeedEdits((current) => {
            const next = { ...current };
            delete next[podcastFeedEditKey(row, podcast)];
            return next;
        });
        setStatus({ kind: "ok", message: `${podcast.title} RSS saved.` });
        startTransition(() => router.refresh());
    }

    async function addManualPodcastFeed(row: AdminComedianListItem) {
        const feedUrl = manualPodcastFeedValue(row).trim();
        if (!feedUrl) return;

        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: {
            podcast: {
                id: number;
                slug: string;
                title: string;
                feedUrl: string | null;
            };
        };
        try {
            body = await adminRequest<{
                podcast: {
                    id: number;
                    slug: string;
                    title: string;
                    feedUrl: string | null;
                };
            }>("/api/admin/podcast-ownership-reviews", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    comedianId: row.id,
                    feedUrl,
                    reason: `Manual RSS feed added from comedian admin for ${row.name}`,
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
        const podcast = body.podcast;
        replacePodcastForRow(row.id, {
            id: podcast.id,
            slug: podcast.slug,
            title: podcast.title,
            feedUrl: podcast.feedUrl,
            websiteUrl: null,
            associationType: "host",
            source: "manual_rss",
            reviewStatus: "accepted",
            confidence: 1,
        });
        setManualPodcastFeedUrls((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${podcast.title} RSS added.` });
        startTransition(() => router.refresh());
    }

    async function publishImage(
        row: AdminComedianListItem,
        slot?: "headshot" | "hero",
        overrideFile?: File,
    ) {
        const stateInputs = manualImageUrlValue(row);
        const inputs: ManualImageUrls = {
            ...stateInputs,
            ...(overrideFile && slot === "headshot"
                ? { headshotFile: overrideFile }
                : {}),
            ...(overrideFile && slot === "hero"
                ? { heroFile: overrideFile }
                : {}),
        };
        const includeHeadshot =
            slot === "headshot" ||
            (!slot && imageSlotHasInput(row, "headshot"));
        const includeHero =
            slot === "hero" || (!slot && imageSlotHasInput(row, "hero"));
        if (!includeHeadshot && !includeHero) return;

        setStatus({ kind: "idle" });
        setImageStatusByRow((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });

        const validationFailures: string[] = [];
        if (includeHeadshot && inputs.headshotFile) {
            const result = await validateComedianImageFile(
                inputs.headshotFile,
                "headshot",
            );
            if (!result.ok) validationFailures.push(result.reason);
        }
        if (includeHero && inputs.heroFile) {
            const result = await validateComedianImageFile(
                inputs.heroFile,
                "hero",
            );
            if (!result.ok) validationFailures.push(result.reason);
        }
        if (validationFailures.length > 0) {
            const message = validationFailures.join("; ");
            setStatus({ kind: "error", message });
            setImageStatusByRow((current) => ({
                ...current,
                [row.id]: { kind: "error", message },
            }));
            return;
        }

        setPendingId(row.id);

        let body: {
            asset: NonNullable<AdminComedianListItem["activeImageAsset"]>;
        };
        try {
            const hasFile =
                (includeHeadshot && inputs.headshotFile) ||
                (includeHero && inputs.heroFile);
            if (hasFile) {
                const formData = new FormData();
                formData.set("comedianId", String(row.id));
                if (includeHeadshot) {
                    if (inputs.headshotFile) {
                        formData.set("headshotFile", inputs.headshotFile);
                    } else if (inputs.headshot.trim()) {
                        formData.set(
                            "headshotImageUrl",
                            inputs.headshot.trim(),
                        );
                    }
                }
                if (includeHero) {
                    if (inputs.heroFile) {
                        formData.set("heroFile", inputs.heroFile);
                    } else if (inputs.hero.trim()) {
                        formData.set("heroImageUrl", inputs.hero.trim());
                    }
                }
                body = await adminRequest<{
                    asset: NonNullable<
                        AdminComedianListItem["activeImageAsset"]
                    >;
                }>("/api/admin/comedians/images/publish", {
                    method: "POST",
                    body: formData,
                });
            } else {
                body = await adminRequest<{
                    asset: NonNullable<
                        AdminComedianListItem["activeImageAsset"]
                    >;
                }>("/api/admin/comedians/images/publish", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        comedianId: row.id,
                        ...(includeHeadshot && inputs.headshot.trim()
                            ? {
                                  headshotImageUrl: inputs.headshot.trim(),
                              }
                            : {}),
                        ...(includeHero && inputs.hero.trim()
                            ? { heroImageUrl: inputs.hero.trim() }
                            : {}),
                    }),
                });
            }
        } catch (error) {
            setPendingId(null);
            const message =
                error instanceof Error ? error.message : "Network error";
            setStatus({ kind: "error", message });
            setImageStatusByRow((current) => ({
                ...current,
                [row.id]: { kind: "error", message },
            }));
            return;
        }

        setPendingId(null);
        onRowChange({
            ...row,
            hasImage: true,
            activeImageAsset: {
                id: body.asset.id,
                sourceImageUrl: body.asset.sourceImageUrl,
                avatarPath: body.asset.avatarPath,
                heroPath: body.asset.heroPath,
                avatarUrl: body.asset.avatarUrl,
                heroUrl: body.asset.heroUrl,
                mimeType: body.asset.mimeType,
                width: body.asset.width,
                height: body.asset.height,
            },
        });
        setManualImageUrls((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        const successMessage = `${row.name} ${
            slot ? `${slot} image` : "images"
        } published.`;
        setStatus({ kind: "ok", message: successMessage });
        setImageStatusByRow((current) => ({
            ...current,
            [row.id]: { kind: "ok", message: successMessage },
        }));
        startTransition(() => router.refresh());
    }

    async function removeImage(
        row: AdminComedianListItem,
        slot: "all" | "thumbnail" | "hero" = "all",
    ) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let body: { hasImage: boolean };
        try {
            body = await adminRequest<{ hasImage: boolean }>(
                "/api/admin/comedians/images",
                {
                    method: "DELETE",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ comedianId: row.id, slot }),
                },
            );
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
        onRowChange({
            ...row,
            hasImage: Boolean(body.hasImage),
            activeImageAsset: body.hasImage
                ? row.activeImageAsset
                    ? {
                          ...row.activeImageAsset,
                          avatarPath:
                              slot === "thumbnail"
                                  ? null
                                  : row.activeImageAsset.avatarPath,
                          avatarUrl:
                              slot === "thumbnail"
                                  ? null
                                  : row.activeImageAsset.avatarUrl,
                          heroPath:
                              slot === "hero"
                                  ? null
                                  : row.activeImageAsset.heroPath,
                          heroUrl:
                              slot === "hero"
                                  ? null
                                  : row.activeImageAsset.heroUrl,
                      }
                    : null
                : null,
            nameImageUrl: body.hasImage ? row.nameImageUrl : "",
        });
        setManualImageUrls((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setStatus({
            kind: "ok",
            message:
                slot === "thumbnail"
                    ? `${row.name} thumbnail removed.`
                    : slot === "hero"
                      ? `${row.name} hero removed.`
                      : `${row.name} images removed.`,
        });
        startTransition(() => router.refresh());
    }

    const parent = parentValue(row);
    const candidates = parentCandidates(row);
    const disabled = globallyDisabled || pendingId !== null || isPending;
    const rowOpen = openComedianRows.has(row.id);
    const currentAvatar = currentAvatarUrl(row);
    const acceptedPodcasts = acceptedAttributedPodcasts(row);
    const pendingPodcastCandidateReviews = row.podcastCandidateReviews.filter(
        (review) => review.candidateStatus === "pending",
    );
    const relationshipOpen = openChildrenSections.has(row.id);
    const imageOpen = openImageSections.has(row.id);
    const socialOpen = openSocialSections.has(row.id);
    const podcastOpen = openPodcastSections.has(row.id);

    return (
        <>
            {row.isBlocked ? (
                <BlockedComedianRow
                    row={row}
                    open={rowOpen}
                    disabled={disabled || pendingId === row.id}
                    onToggle={() => toggleComedianRow(row.id)}
                    onUnblock={() => void unblockComedian(row)}
                />
            ) : (
                <li className="px-4 py-3">
                    <button
                        type="button"
                        aria-expanded={rowOpen}
                        aria-controls={`comedian-row-${row.id}`}
                        onClick={() => toggleComedianRow(row.id)}
                        className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-coconut-cream/55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-copper/40"
                    >
                        {rowOpen ? (
                            <ChevronDown className="h-4 w-4 shrink-0 text-cedar" />
                        ) : (
                            <ChevronRight className="h-4 w-4 shrink-0 text-cedar" />
                        )}
                        <ComedianRowHeadshot row={row} />
                        <span className="min-w-0 flex-1">
                            <span
                                role="heading"
                                aria-level={2}
                                className="block break-words font-urbanist-bold text-h3 leading-tight text-cedar"
                            >
                                {row.name}
                            </span>
                            <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-dmSans text-caption text-soft-charcoal">
                                <span>ID {row.id}</span>
                                <span>
                                    {row.totalShows.toLocaleString()} shows
                                </span>
                                <span>
                                    {acceptedPodcasts.length.toLocaleString()}{" "}
                                    podcasts
                                </span>
                            </span>
                        </span>
                        <span className="shrink-0 rounded-md border border-green-700/25 bg-green-50 px-2.5 py-1 font-dmSans text-caption font-semibold text-green-950">
                            Active
                        </span>
                    </button>
                    <div
                        id={`comedian-row-${row.id}`}
                        hidden={!rowOpen}
                        className={`mt-4 min-w-0 space-y-5 ${
                            rowOpen ? "" : "hidden"
                        }`}
                    >
                        <div className="col-span-full rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                            <div className="flex flex-wrap gap-2">
                                <SummaryPill label="ID" value={row.id} />
                                <SummaryPill
                                    label="Popularity"
                                    value={row.popularity.toLocaleString()}
                                />
                                <SummaryPill
                                    label="Shows"
                                    value={row.totalShows.toLocaleString()}
                                />
                                <SummaryPill
                                    label="Children"
                                    value={children.length.toLocaleString()}
                                />
                                <SummaryPill
                                    label="Podcasts"
                                    value={acceptedPodcasts.length.toLocaleString()}
                                />
                                <SummaryPill
                                    label="State"
                                    value="Not blocked"
                                    tone="good"
                                />
                            </div>
                            <div className="mt-3 font-dmSans text-caption text-soft-charcoal">
                                {row.latestTicketPurchase ? (
                                    <span className="inline-flex min-w-0 flex-wrap items-center gap-1">
                                        <a
                                            href={row.latestTicketPurchase.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex min-w-0 items-center gap-1 font-semibold text-copper-dark hover:underline"
                                        >
                                            <span>Latest ticket purchase</span>
                                            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                                        </a>
                                        <span className="text-soft-charcoal">
                                            ·{" "}
                                            {row.latestTicketPurchase
                                                .showName ??
                                                "Untitled show"}{" "}
                                            ·{" "}
                                            {row.latestTicketPurchase.clubName}{" "}
                                            ·{" "}
                                            {formatDate(
                                                row.latestTicketPurchase
                                                    .showDate,
                                            )}
                                        </span>
                                    </span>
                                ) : (
                                    <span>No ticket purchase link found.</span>
                                )}
                            </div>
                        </div>
                        <div
                            role="group"
                            aria-label={`Comedian editor for ${row.name}`}
                            className="col-span-full rounded-md border border-copper/20 bg-white p-4 font-dmSans shadow-sm"
                        >
                            <ComedianProfileSection rowName={row.name}>
                                <div className="min-w-0 space-y-3">
                                    <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Display name
                                    </label>
                                    <div className="mt-1 flex flex-wrap items-center gap-2 sm:flex-nowrap">
                                        <input
                                            aria-label="Comedian name"
                                            type="text"
                                            value={nameValue(row)}
                                            onChange={(event) =>
                                                setNameEdits((current) => ({
                                                    ...current,
                                                    [row.id]:
                                                        event.target.value,
                                                }))
                                            }
                                            className="min-w-[220px] flex-1 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled ||
                                                pendingId === row.id ||
                                                !isRecordDirty(row) ||
                                                !normalizedAdminName(
                                                    nameValue(row),
                                                )
                                            }
                                            onClick={() =>
                                                void saveComedianRecord(row)
                                            }
                                        >
                                            <Save className="h-4 w-4" />
                                            Save record
                                        </Button>
                                    </div>
                                </div>
                                <div>
                                    <div className="mb-2 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Blocklist state
                                    </div>
                                    <label className="inline-flex w-fit items-center gap-2 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar">
                                        <input
                                            type="checkbox"
                                            checked={false}
                                            disabled={
                                                disabled || pendingId === row.id
                                            }
                                            onChange={() =>
                                                void blockComedian(row)
                                            }
                                            aria-label={`Blocked status for ${row.name}`}
                                            className="h-4 w-4 accent-red-800 disabled:accent-soft-charcoal"
                                        />
                                        Blocked
                                    </label>
                                </div>
                            </ComedianProfileSection>
                            <div
                                role="list"
                                aria-label={`Comedian detail sections for ${row.name}`}
                                className="mt-4 space-y-3"
                            >
                                <ComedianSocialSection
                                    rowId={row.id}
                                    open={socialOpen}
                                    onToggle={() => toggleSocialSection(row.id)}
                                >
                                    <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Website
                                        <input
                                            aria-label="Comedian website"
                                            type="url"
                                            value={profileFieldValue(
                                                row,
                                                "website",
                                            )}
                                            onChange={(event) =>
                                                updateProfileEdit(row, {
                                                    website: event.target.value,
                                                })
                                            }
                                            placeholder="https://example.com"
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Tour scrape URL
                                        <input
                                            aria-label="Comedian website scraping URL"
                                            type="url"
                                            value={profileFieldValue(
                                                row,
                                                "websiteScrapingUrl",
                                            )}
                                            onChange={(event) =>
                                                updateProfileEdit(row, {
                                                    websiteScrapingUrl:
                                                        event.target.value,
                                                })
                                            }
                                            placeholder="https://example.com/tour"
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Instagram
                                        <input
                                            aria-label="Comedian Instagram handle"
                                            type="text"
                                            value={profileFieldValue(
                                                row,
                                                "instagramAccount",
                                            )}
                                            onChange={(event) =>
                                                updateProfileEdit(row, {
                                                    instagramAccount:
                                                        event.target.value,
                                                })
                                            }
                                            placeholder="handle (without @)"
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        TikTok
                                        <input
                                            aria-label="Comedian TikTok handle"
                                            type="text"
                                            value={profileFieldValue(
                                                row,
                                                "tiktokAccount",
                                            )}
                                            onChange={(event) =>
                                                updateProfileEdit(row, {
                                                    tiktokAccount:
                                                        event.target.value,
                                                })
                                            }
                                            placeholder="handle (without @)"
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <div
                                        role="group"
                                        aria-label="YouTube"
                                        className="grid gap-3 rounded-md border border-copper/20 bg-white p-3"
                                    >
                                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            YouTube
                                        </div>
                                        <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Handle
                                            <input
                                                aria-label="Comedian YouTube handle"
                                                type="text"
                                                value={profileFieldValue(
                                                    row,
                                                    "youtubeAccount",
                                                )}
                                                onChange={(event) =>
                                                    updateProfileEdit(row, {
                                                        youtubeAccount:
                                                            event.target.value,
                                                    })
                                                }
                                                placeholder="@handle or channel id"
                                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            />
                                        </label>
                                        <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Channel ID
                                            <input
                                                aria-label="Comedian YouTube channel ID"
                                                type="text"
                                                value={profileFieldValue(
                                                    row,
                                                    "youtubeChannelId",
                                                )}
                                                onChange={(event) =>
                                                    updateProfileEdit(row, {
                                                        youtubeChannelId:
                                                            event.target.value,
                                                    })
                                                }
                                                placeholder="UC..."
                                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            />
                                        </label>
                                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            YouTube WebSub
                                        </div>
                                        <div className="mt-2 grid gap-2 font-dmSans text-caption text-soft-charcoal sm:grid-cols-2">
                                            <div>
                                                <span className="font-semibold text-cedar">
                                                    Subscription
                                                </span>{" "}
                                                {row.subscriptionStatus ??
                                                    "none"}
                                            </div>
                                            <div>
                                                <span className="font-semibold text-cedar">
                                                    Recent event
                                                </span>{" "}
                                                {row.recentEventStatus ??
                                                    "none"}
                                            </div>
                                            {row.lastSubscribeError ? (
                                                <div className="sm:col-span-2 text-red-700">
                                                    {row.lastSubscribeError}
                                                </div>
                                            ) : null}
                                        </div>
                                        <div className="mt-3 flex flex-wrap gap-3">
                                            <label className="inline-flex w-fit items-center gap-2 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar">
                                                <input
                                                    type="checkbox"
                                                    checked={
                                                        row.youtubeLiveFeedEnabled ??
                                                        false
                                                    }
                                                    disabled={
                                                        disabled ||
                                                        !row.youtubeChannelId ||
                                                        savingWebSubKey ===
                                                            `${row.uuid}:youtubeLiveFeedEnabled`
                                                    }
                                                    onChange={(event) =>
                                                        void saveYouTubeWebSubFlag(
                                                            row,
                                                            "youtubeLiveFeedEnabled",
                                                            event.target
                                                                .checked,
                                                        )
                                                    }
                                                    aria-label={`Live feed for ${row.name}`}
                                                    className="h-4 w-4 accent-copper-dark disabled:accent-soft-charcoal"
                                                />
                                                Live feed
                                            </label>
                                            <label className="inline-flex w-fit items-center gap-2 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar">
                                                <input
                                                    type="checkbox"
                                                    checked={
                                                        row.youtubeLiveNotificationsEnabled ??
                                                        false
                                                    }
                                                    disabled={
                                                        disabled ||
                                                        !row.youtubeChannelId ||
                                                        savingWebSubKey ===
                                                            `${row.uuid}:youtubeLiveNotificationsEnabled`
                                                    }
                                                    onChange={(event) =>
                                                        void saveYouTubeWebSubFlag(
                                                            row,
                                                            "youtubeLiveNotificationsEnabled",
                                                            event.target
                                                                .checked,
                                                        )
                                                    }
                                                    aria-label={`Notifications for ${row.name}`}
                                                    className="h-4 w-4 accent-copper-dark disabled:accent-soft-charcoal"
                                                />
                                                Notifications
                                            </label>
                                            {!row.youtubeChannelId ? (
                                                <span className="self-center font-dmSans text-caption text-soft-charcoal">
                                                    Add a YouTube channel ID to
                                                    enable WebSub.
                                                </span>
                                            ) : null}
                                        </div>
                                    </div>
                                    <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Linktree
                                        <input
                                            aria-label="Comedian Linktree URL"
                                            type="url"
                                            value={profileFieldValue(
                                                row,
                                                "linktree",
                                            )}
                                            onChange={(event) =>
                                                updateProfileEdit(row, {
                                                    linktree:
                                                        event.target.value,
                                                })
                                            }
                                            placeholder="https://linktr.ee/..."
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <div className="flex justify-end">
                                        <Button
                                            type="button"
                                            className="gap-2 bg-copper-dark text-white hover:bg-cedar disabled:bg-gray-300 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled ||
                                                pendingId === row.id ||
                                                !isRecordDirty(row) ||
                                                !normalizedAdminName(
                                                    nameValue(row),
                                                )
                                            }
                                            onClick={() =>
                                                void saveComedianRecord(row)
                                            }
                                        >
                                            <Save className="h-4 w-4" />
                                            Update Comedian
                                        </Button>
                                    </div>
                                </ComedianSocialSection>

                                <ComedianRelationshipSection
                                    rowId={row.id}
                                    open={relationshipOpen}
                                    childCount={children.length}
                                    onToggle={() =>
                                        toggleChildrenSection(row.id)
                                    }
                                >
                                    <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Current parent
                                    </div>
                                    {parent ? (
                                        <div className="flex max-w-full items-center gap-2 rounded-md border border-green-700/40 bg-green-50 px-3 py-2 font-dmSans text-body font-semibold text-green-950">
                                            <span className="min-w-0 truncate">
                                                {parent.name}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setSelectedParents(
                                                        (current) => ({
                                                            ...current,
                                                            [row.id]: null,
                                                        }),
                                                    )
                                                }
                                                className="ml-auto shrink-0 rounded-sm p-1 text-green-950 hover:bg-green-100"
                                                aria-label={`Clear parent for ${row.name}`}
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="rounded-md border border-soft-charcoal/20 bg-gray-50 px-3 py-2 font-dmSans text-body text-soft-charcoal">
                                            No parent assigned
                                        </div>
                                    )}

                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Find parent
                                        <input
                                            type="search"
                                            value={parentSearches[row.id] ?? ""}
                                            onChange={(event) =>
                                                setParentSearches(
                                                    (current) => ({
                                                        ...current,
                                                        [row.id]:
                                                            event.target.value,
                                                    }),
                                                )
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            placeholder="Search parent name"
                                        />
                                    </label>
                                    {candidates.length > 0 && (
                                        <div className="flex flex-wrap gap-2">
                                            {candidates.map((candidate) => (
                                                <button
                                                    key={candidate.id}
                                                    type="button"
                                                    onClick={() =>
                                                        setSelectedParents(
                                                            (current) => ({
                                                                ...current,
                                                                [row.id]: {
                                                                    id: candidate.id,
                                                                    name: candidate.name,
                                                                },
                                                            }),
                                                        )
                                                    }
                                                    className="rounded-md border border-copper/40 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar hover:bg-copper/10"
                                                >
                                                    {candidate.name}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={
                                            disabled ||
                                            !isParentDirty(row) ||
                                            pendingId === row.id
                                        }
                                        onClick={() => void saveParent(row)}
                                    >
                                        <Save className="h-4 w-4" />
                                        Save relationship
                                    </Button>
                                    {children.length > 0 ? (
                                        <ul className="divide-y divide-copper/15 overflow-hidden rounded-md border border-copper/20 bg-white">
                                            {children.map((child) => (
                                                <li
                                                    key={child.id}
                                                    className="flex flex-wrap items-center gap-3 px-3 py-2 sm:flex-nowrap"
                                                >
                                                    <ComedianRowHeadshot
                                                        row={child}
                                                    />
                                                    <span className="min-w-0 flex-1 break-words font-urbanist-bold text-body text-cedar">
                                                        {child.name}
                                                    </span>
                                                    <span className="shrink-0 font-dmSans text-caption font-semibold text-soft-charcoal">
                                                        ID {child.id}
                                                    </span>
                                                    <Button
                                                        type="button"
                                                        variant="outline"
                                                        className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                        disabled={
                                                            disabled ||
                                                            pendingId ===
                                                                child.id
                                                        }
                                                        onClick={() =>
                                                            void saveParent(
                                                                child,
                                                                null,
                                                            )
                                                        }
                                                    >
                                                        <X className="h-4 w-4" />
                                                        Remove parent
                                                    </Button>
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <div className="rounded-md border border-soft-charcoal/20 bg-white px-3 py-2 font-dmSans text-body text-soft-charcoal">
                                            No child profiles.
                                        </div>
                                    )}
                                </ComedianRelationshipSection>

                                <ComedianPodcastSection
                                    rowId={row.id}
                                    open={podcastOpen}
                                    attributedCount={acceptedPodcasts.length}
                                    pendingCount={
                                        pendingPodcastCandidateReviews.length
                                    }
                                    onToggle={() =>
                                        togglePodcastSection(row.id)
                                    }
                                >
                                    <div>
                                        <div className="mb-3 text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Podcast RSS
                                        </div>
                                        {acceptedPodcasts.length > 0 ? (
                                            <div className="grid gap-3 lg:grid-cols-2">
                                                {acceptedPodcasts.map(
                                                    (podcast) => {
                                                        const feedValue =
                                                            podcastFeedValue(
                                                                row,
                                                                podcast,
                                                            );
                                                        const feedDirty =
                                                            feedValue.trim() !==
                                                            (podcast.feedUrl ??
                                                                "");
                                                        return (
                                                            <div
                                                                key={podcast.id}
                                                                className="space-y-2"
                                                            >
                                                                <div className="flex flex-wrap items-center gap-2">
                                                                    <div className="font-semibold text-cedar">
                                                                        {
                                                                            podcast.title
                                                                        }
                                                                    </div>
                                                                    <a
                                                                        href={`/podcast/${podcast.slug}`}
                                                                        target="_blank"
                                                                        className="inline-flex items-center gap-1 text-caption font-semibold text-copper-dark hover:underline"
                                                                    >
                                                                        Public
                                                                        <ExternalLink className="h-3.5 w-3.5" />
                                                                    </a>
                                                                    {podcast.feedUrl && (
                                                                        <a
                                                                            href={
                                                                                podcast.feedUrl
                                                                            }
                                                                            target="_blank"
                                                                            rel="noreferrer"
                                                                            className="inline-flex items-center gap-1 text-caption font-semibold text-copper-dark hover:underline"
                                                                        >
                                                                            RSS
                                                                            <ExternalLink className="h-3.5 w-3.5" />
                                                                        </a>
                                                                    )}
                                                                </div>
                                                                <label className="grid gap-1 text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                                    RSS feed for{" "}
                                                                    {
                                                                        podcast.title
                                                                    }
                                                                    <input
                                                                        aria-label={`RSS feed for ${podcast.title}`}
                                                                        type="url"
                                                                        value={
                                                                            feedValue
                                                                        }
                                                                        onChange={(
                                                                            event,
                                                                        ) =>
                                                                            updatePodcastFeedValue(
                                                                                row,
                                                                                podcast,
                                                                                event
                                                                                    .target
                                                                                    .value,
                                                                            )
                                                                        }
                                                                        placeholder="https://example.com/rss.xml"
                                                                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                                    />
                                                                </label>
                                                                <div className="flex flex-wrap gap-2">
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                                        disabled={
                                                                            disabled ||
                                                                            pendingId ===
                                                                                row.id ||
                                                                            !feedDirty ||
                                                                            !feedValue.trim()
                                                                        }
                                                                        onClick={() =>
                                                                            void savePodcastFeedUrl(
                                                                                row,
                                                                                podcast,
                                                                                feedValue.trim(),
                                                                            )
                                                                        }
                                                                    >
                                                                        <Save className="h-4 w-4" />
                                                                        Save RSS
                                                                    </Button>
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        className="gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                                        disabled={
                                                                            disabled ||
                                                                            pendingId ===
                                                                                row.id ||
                                                                            !podcast.feedUrl
                                                                        }
                                                                        onClick={() =>
                                                                            void savePodcastFeedUrl(
                                                                                row,
                                                                                podcast,
                                                                                null,
                                                                            )
                                                                        }
                                                                    >
                                                                        <X className="h-4 w-4" />
                                                                        Remove
                                                                        RSS
                                                                    </Button>
                                                                </div>
                                                            </div>
                                                        );
                                                    },
                                                )}
                                            </div>
                                        ) : (
                                            <div className="max-w-3xl space-y-2">
                                                <label className="grid gap-1 text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                    RSS feed URL
                                                    <input
                                                        aria-label={`RSS feed URL for ${row.name}`}
                                                        type="url"
                                                        value={manualPodcastFeedValue(
                                                            row,
                                                        )}
                                                        onChange={(event) =>
                                                            setManualPodcastFeedUrls(
                                                                (current) => ({
                                                                    ...current,
                                                                    [row.id]:
                                                                        event
                                                                            .target
                                                                            .value,
                                                                }),
                                                            )
                                                        }
                                                        placeholder="https://example.com/rss.xml"
                                                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                    />
                                                </label>
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                    disabled={
                                                        disabled ||
                                                        pendingId === row.id ||
                                                        !manualPodcastFeedValue(
                                                            row,
                                                        ).trim()
                                                    }
                                                    onClick={() =>
                                                        void addManualPodcastFeed(
                                                            row,
                                                        )
                                                    }
                                                >
                                                    <Save className="h-4 w-4" />
                                                    Save RSS
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                    {pendingPodcastCandidateReviews.length >
                                        0 && (
                                        <div className="border-t border-copper/20 pt-4">
                                            <div className="mb-3 text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Podcast host reviews
                                            </div>
                                            <div className="grid gap-3">
                                                {pendingPodcastCandidateReviews.map(
                                                    (review) => {
                                                        const podcast =
                                                            review.podcast;
                                                        const isBlocked =
                                                            Boolean(
                                                                podcast?.denyListEntry,
                                                            );
                                                        return (
                                                            <div
                                                                key={review.id}
                                                                className="grid gap-3 rounded-md border border-copper/20 bg-white/80 p-3 lg:grid-cols-[minmax(0,1fr)_auto]"
                                                            >
                                                                <div className="min-w-0">
                                                                    <div className="flex flex-wrap items-center gap-2">
                                                                        <div className="font-dmSans text-body font-semibold text-cedar">
                                                                            {podcast?.title ??
                                                                                review.sourcePodcastId}
                                                                        </div>
                                                                        <span className="rounded-md border border-soft-charcoal/20 bg-gray-50 px-2 py-1 font-dmSans text-caption font-semibold text-soft-charcoal">
                                                                            {
                                                                                review.candidateStatus
                                                                            }
                                                                        </span>
                                                                        {isBlocked && (
                                                                            <span className="rounded-md border border-red-700/30 bg-red-50 px-2 py-1 font-dmSans text-caption font-semibold text-red-900">
                                                                                Blocked
                                                                            </span>
                                                                        )}
                                                                        <span className="font-dmSans text-caption text-soft-charcoal">
                                                                            {formatPercent(
                                                                                review.confidence,
                                                                            )}
                                                                        </span>
                                                                    </div>
                                                                    {podcast?.authorName && (
                                                                        <div className="mt-1 font-dmSans text-caption text-soft-charcoal">
                                                                            by{" "}
                                                                            {
                                                                                podcast.authorName
                                                                            }
                                                                        </div>
                                                                    )}
                                                                    <div className="mt-2 flex flex-wrap gap-3 font-dmSans text-caption">
                                                                        {podcast && (
                                                                            <a
                                                                                href={`/podcast/${podcast.slug}`}
                                                                                target="_blank"
                                                                                className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                                            >
                                                                                Public
                                                                                page
                                                                                <ExternalLink className="h-3.5 w-3.5" />
                                                                            </a>
                                                                        )}
                                                                        {podcast?.feedUrl ? (
                                                                            <a
                                                                                href={
                                                                                    podcast.feedUrl
                                                                                }
                                                                                target="_blank"
                                                                                rel="noreferrer"
                                                                                className="inline-flex max-w-full items-center gap-1 text-copper-dark hover:underline"
                                                                            >
                                                                                <span className="truncate">
                                                                                    RSS:{" "}
                                                                                    {
                                                                                        podcast.feedUrl
                                                                                    }
                                                                                </span>
                                                                                <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                                                                            </a>
                                                                        ) : (
                                                                            <span className="text-soft-charcoal">
                                                                                RSS
                                                                                feed
                                                                                missing
                                                                            </span>
                                                                        )}
                                                                        {podcast?.websiteUrl && (
                                                                            <a
                                                                                href={
                                                                                    podcast.websiteUrl
                                                                                }
                                                                                target="_blank"
                                                                                rel="noreferrer"
                                                                                className="inline-flex max-w-full items-center gap-1 text-copper-dark hover:underline"
                                                                            >
                                                                                Website
                                                                                <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                                                                            </a>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        className="gap-2 border-green-800/40 bg-white text-green-950 hover:bg-green-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                                        disabled={
                                                                            disabled ||
                                                                            pendingId ===
                                                                                row.id ||
                                                                            isBlocked
                                                                        }
                                                                        onClick={() =>
                                                                            void reviewPodcastCandidate(
                                                                                row,
                                                                                review,
                                                                                "podcast-review-accept-host",
                                                                            )
                                                                        }
                                                                    >
                                                                        <Save className="h-4 w-4" />
                                                                        Accept
                                                                        as host
                                                                    </Button>
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                                        disabled={
                                                                            disabled ||
                                                                            pendingId ===
                                                                                row.id ||
                                                                            isBlocked
                                                                        }
                                                                        onClick={() =>
                                                                            void reviewPodcastCandidate(
                                                                                row,
                                                                                review,
                                                                                "podcast-review-reject-host",
                                                                            )
                                                                        }
                                                                    >
                                                                        <X className="h-4 w-4" />
                                                                        Reject
                                                                        as host
                                                                    </Button>
                                                                </div>
                                                            </div>
                                                        );
                                                    },
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </ComedianPodcastSection>
                                <ComedianImageSection
                                    rowId={row.id}
                                    open={imageOpen}
                                    onToggle={() => toggleImageSection(row.id)}
                                >
                                    <div className="grid min-w-0 gap-3 lg:max-w-3xl">
                                        <AdminImageEditor
                                            id={`headshot-${row.id}`}
                                            title="Headshot"
                                            currentImage={
                                                currentAvatar
                                                    ? {
                                                          url: currentAvatar,
                                                          alt: `${row.name} current headshot image`,
                                                          className:
                                                              "h-24 w-24 rounded-md border border-copper/20 object-cover",
                                                      }
                                                    : undefined
                                            }
                                            emptyClassName="flex h-24 w-24 items-center justify-center rounded-md border border-dashed border-soft-charcoal/30 bg-gray-50 font-dmSans text-caption text-soft-charcoal"
                                            urlInput={{
                                                label: "Headshot image URL",
                                                ariaLabel: "Headshot image URL",
                                                value: manualImageUrlValue(row)
                                                    .headshot,
                                                placeholder:
                                                    "https://example.com/headshot.jpg",
                                                saveAriaLabel:
                                                    "Save headshot URL",
                                                canSave: Boolean(
                                                    manualImageUrlValue(
                                                        row,
                                                    ).headshot.trim() &&
                                                        manualImageUrlValue(
                                                            row,
                                                        ).headshot.trim() !==
                                                            currentAvatar,
                                                ),
                                                onChange: (value) =>
                                                    updateManualImageUrls(row, {
                                                        headshot: value,
                                                        headshotFile: null,
                                                    }),
                                                onSave: () =>
                                                    void publishImage(
                                                        row,
                                                        "headshot",
                                                    ),
                                            }}
                                            fileInput={{
                                                ariaLabel:
                                                    "Upload headshot file",
                                                chooseLabel:
                                                    "Choose headshot file",
                                                guidance:
                                                    "1:1 square, at least 600x600",
                                                stagedFile:
                                                    manualImageUrlValue(row)
                                                        .headshotFile,
                                                pendingLabel:
                                                    "Pending headshot",
                                                pendingAlt: `${row.name} pending headshot`,
                                                previewClassName:
                                                    "h-16 w-16 shrink-0 rounded-md border border-copper/30 object-cover",
                                                onSelect: (file) =>
                                                    stageImageFile(
                                                        row,
                                                        "headshot",
                                                        file,
                                                    ),
                                                onPublish: () =>
                                                    void publishImage(
                                                        row,
                                                        "headshot",
                                                    ),
                                                onDiscard: () =>
                                                    discardStagedFile(
                                                        row,
                                                        "headshot",
                                                    ),
                                            }}
                                            status={imageStatusByRow[row.id]}
                                            disabled={
                                                disabled || pendingId === row.id
                                            }
                                            remove={{
                                                visible: Boolean(
                                                    row.activeImageAsset
                                                        ?.avatarPath,
                                                ),
                                                label: "Remove thumbnail",
                                                onRemove: () =>
                                                    void removeImage(
                                                        row,
                                                        "thumbnail",
                                                    ),
                                            }}
                                        />
                                    </div>

                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="mt-3 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={
                                            disabled ||
                                            pendingId === row.id ||
                                            !imageSlotHasInput(row, "headshot")
                                        }
                                        onClick={() =>
                                            void publishImage(row, "headshot")
                                        }
                                    >
                                        <Upload className="h-4 w-4" />
                                        Upload changed images
                                    </Button>

                                    {row.activeImageAsset ? (
                                        <div className="mt-3 font-dmSans text-caption text-soft-charcoal">
                                            Source{" "}
                                            {formatDimensions(
                                                row.activeImageAsset.width,
                                                row.activeImageAsset.height,
                                            )}
                                        </div>
                                    ) : null}

                                    {row.hasImage && (
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="mt-3 gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled || pendingId === row.id
                                            }
                                            onClick={() =>
                                                void removeImage(row, "all")
                                            }
                                        >
                                            <Trash2 className="h-4 w-4" />
                                            Remove all images
                                        </Button>
                                    )}
                                </ComedianImageSection>
                            </div>
                        </div>
                    </div>
                </li>
            )}
        </>
    );
}
