"use client";

import { Ban, ExternalLink, Save, Search } from "lucide-react";
import { Button } from "@/ui/components/ui/button";
import { AdminPodcastHostshipAssignmentControls } from "./AdminPodcastHostshipAssignmentControls";
import { AdminPodcastHostshipReviewGroupFrame } from "./AdminPodcastHostshipReviewGroupFrame";
import type {
    ComedianOption,
    PodcastReviewGroup,
    SearchResult,
} from "./AdminPodcastHostshipReviewModels";
import {
    evidencePreview,
    formatDate,
    formatPercent,
} from "./AdminPodcastHostshipReviewModels";

type Props = {
    group: PodcastReviewGroup;
    selectedHost: ComedianOption | null;
    selectedCohosts: ComedianOption[];
    note: string;
    searchTerm: string;
    searchResults: SearchResult[];
    collapsed: boolean;
    disabled: boolean;
    searching: boolean;
    onToggle: (key: string) => void;
    onSelectHost: (key: string, option: ComedianOption) => void;
    onRemoveHost: (key: string) => void;
    onToggleCohost: (
        key: string,
        option: ComedianOption,
        selected: boolean,
    ) => void;
    onNoteChange: (key: string, value: string) => void;
    onSearchTermChange: (key: string, value: string) => void;
    onSearch: (key: string) => void;
    onSave: (
        group: PodcastReviewGroup,
        hostOverride?: ComedianOption | null,
        denyListed?: boolean,
    ) => void;
};

export function AdminPodcastHostshipPodcastCard({
    group,
    selectedHost,
    selectedCohosts,
    note,
    searchTerm,
    searchResults,
    collapsed,
    disabled,
    searching,
    onToggle,
    onSelectHost,
    onRemoveHost,
    onToggleCohost,
    onNoteChange,
    onSearchTermChange,
    onSearch,
    onSave,
}: Props) {
    const isDenied = Boolean(group.podcast.denyListEntry);
    const frameKey = `podcast-${group.key}`;
    const noteId = `podcast-review-note-${group.key}`;
    const searchId = `podcast-host-search-${group.key}`;

    return (
        <AdminPodcastHostshipReviewGroupFrame
            groupKey={frameKey}
            title={group.podcast.title}
            subtitle={
                group.podcast.authorName
                    ? `by ${group.podcast.authorName}`
                    : "Author missing"
            }
            summary={`${group.candidates.length} candidate${group.candidates.length === 1 ? "" : "s"} · ${selectedHost ? "approved" : isDenied ? "deny-listed" : "no host"} · popularity ${group.popularity.toFixed(1)}`}
            collapsed={collapsed}
            onToggle={onToggle}
        >
            <div className="grid gap-4">
                <div className="min-w-0 rounded-md border border-gray-200 bg-ecru-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-urbanist-bold text-h3 leading-tight text-cedar">
                            {group.podcast.title}
                        </h2>
                        <span
                            className={`rounded-md px-2 py-1 font-dmSans text-caption font-semibold ${
                                selectedHost
                                    ? "bg-green-50 text-green-800"
                                    : "bg-red-50 text-red-800"
                            }`}
                        >
                            {selectedHost
                                ? "Approved"
                                : isDenied
                                  ? "Deny-listed"
                                  : "No host"}
                        </span>
                    </div>
                    <div className="mt-2 font-dmSans text-body text-soft-charcoal">
                        {group.podcast.authorName && (
                            <span>by {group.podcast.authorName}</span>
                        )}
                    </div>
                    <AdminPodcastHostshipAssignmentControls
                        groupKey={group.key}
                        selectedHost={selectedHost}
                        selectedCohosts={selectedCohosts}
                        isDenied={isDenied}
                        onSelectHost={onSelectHost}
                        onRemoveHost={onRemoveHost}
                        onToggleCohost={onToggleCohost}
                    />
                    {group.podcast.denyListEntry && (
                        <p className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 font-dmSans text-caption text-red-900">
                            Denied{" "}
                            {formatDate(group.podcast.denyListEntry.deniedAt)}
                            {group.podcast.denyListEntry.reason
                                ? `: ${group.podcast.denyListEntry.reason}`
                                : ""}
                        </p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-caption text-soft-charcoal">
                        <span>
                            {group.candidates.length} candidate
                            {group.candidates.length === 1 ? "" : "s"}
                        </span>
                        <span>
                            {group.podcast.feedUrl ??
                                group.candidates[0].sourcePodcastId}
                        </span>
                        <time dateTime={group.candidates[0].createdAt}>
                            {formatDate(group.candidates[0].createdAt)}
                        </time>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-3 font-dmSans text-caption">
                        <a
                            href={`/podcast/${group.podcast.slug}`}
                            className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                        >
                            Public page
                            <ExternalLink
                                className="h-3.5 w-3.5"
                                aria-hidden="true"
                            />
                        </a>
                        {group.podcast.websiteUrl && (
                            <a
                                href={group.podcast.websiteUrl}
                                className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                            >
                                Website
                                <ExternalLink
                                    className="h-3.5 w-3.5"
                                    aria-hidden="true"
                                />
                            </a>
                        )}
                    </div>
                </div>

                <div className="grid gap-4">
                    <AdminPodcastHostshipAssignmentControls
                        groupKey={group.key}
                        selectedHost={selectedHost}
                        selectedCohosts={selectedCohosts}
                        isDenied={isDenied}
                        options={group.comedianOptions}
                        showSummary={false}
                        onSelectHost={onSelectHost}
                        onRemoveHost={onRemoveHost}
                        onToggleCohost={onToggleCohost}
                    />
                    <section
                        aria-labelledby={`podcast-review-controls-${group.key}`}
                        className="grid gap-3 rounded-md border border-gray-200 bg-ecru-white p-3"
                    >
                        <h3
                            id={`podcast-review-controls-${group.key}`}
                            className="font-dmSans text-sm font-semibold text-cedar"
                        >
                            Review controls
                        </h3>
                        <div className="grid gap-3 lg:grid-cols-2">
                            <div className="grid content-start gap-2">
                                <div className="grid gap-1">
                                    <label
                                        htmlFor={searchId}
                                        className="font-dmSans text-sm font-semibold text-cedar"
                                    >
                                        Add host
                                    </label>
                                    <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] md:grid-cols-[minmax(0,1fr)_auto] lg:grid-cols-[minmax(0,1fr)_auto]">
                                        <input
                                            id={searchId}
                                            value={searchTerm}
                                            onChange={(event) =>
                                                onSearchTermChange(
                                                    group.key,
                                                    event.target.value,
                                                )
                                            }
                                            className="min-w-0 w-full rounded-md border border-gray-300 px-3 py-2 font-dmSans text-body font-normal text-foreground focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark"
                                        />
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="gap-2 border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper-dark focus-visible:ring-0"
                                            onClick={() => onSearch(group.key)}
                                            disabled={disabled || searching}
                                        >
                                            <Search
                                                className="h-4 w-4"
                                                aria-hidden="true"
                                            />
                                            Search
                                        </Button>
                                    </div>
                                </div>
                                {searchResults.length > 0 && (
                                    <div className="flex flex-wrap gap-2">
                                        {searchResults.map((result) => (
                                            <button
                                                key={result.id}
                                                type="button"
                                                onClick={() =>
                                                    onSelectHost(group.key, {
                                                        ...result,
                                                        popularity:
                                                            result.popularity ??
                                                            0,
                                                    })
                                                }
                                                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 font-dmSans text-sm font-semibold text-cedar hover:border-copper-dark"
                                            >
                                                {result.name}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <label
                                htmlFor={noteId}
                                className="grid gap-1 font-dmSans text-sm font-semibold text-cedar"
                            >
                                Review note
                                <textarea
                                    id={noteId}
                                    value={note}
                                    onChange={(event) =>
                                        onNoteChange(
                                            group.key,
                                            event.target.value,
                                        )
                                    }
                                    className="min-h-20 rounded-md border border-gray-300 px-3 py-2 font-dmSans text-body font-normal text-foreground focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark"
                                    maxLength={1000}
                                />
                            </label>
                        </div>
                        <div className="flex flex-col flex-wrap gap-2 sm:flex-row md:flex-row lg:flex-row lg:justify-end">
                            <Button
                                type="button"
                                variant="outline"
                                className="gap-2 border-red-700 bg-white !text-red-800 hover:bg-red-700 hover:!text-white disabled:border-gray-300 disabled:bg-gray-100 disabled:!text-soft-charcoal disabled:opacity-100"
                                onClick={() => onSave(group, null, true)}
                                disabled={disabled}
                                aria-label={`Block ${group.podcast.title}`}
                            >
                                <Ban className="h-4 w-4" aria-hidden="true" />
                                Deny-list podcast
                            </Button>
                            {isDenied && (
                                <>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white disabled:border-gray-300 disabled:bg-gray-100 disabled:!text-soft-charcoal disabled:opacity-100"
                                        onClick={() =>
                                            onSave(group, null, false)
                                        }
                                        disabled={disabled}
                                        aria-label={`Restore ${group.podcast.title} without host`}
                                    >
                                        Restore without host
                                    </Button>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white disabled:border-gray-300 disabled:bg-gray-100 disabled:!text-soft-charcoal disabled:opacity-100"
                                        onClick={() =>
                                            onSave(group, undefined, false)
                                        }
                                        disabled={disabled || !selectedHost}
                                        aria-label={`Restore ${group.podcast.title} with host`}
                                    >
                                        Restore with host
                                    </Button>
                                </>
                            )}
                            <Button
                                type="button"
                                className="gap-2 !text-white"
                                variant="roundedShimmer"
                                onClick={() => onSave(group)}
                                disabled={disabled}
                                aria-label={`Save ${group.podcast.title}`}
                            >
                                <Save className="h-4 w-4" aria-hidden="true" />
                                Save
                            </Button>
                        </div>
                    </section>
                </div>
            </div>

            <details className="rounded-md bg-ecru-white p-3">
                <summary className="cursor-pointer font-dmSans text-sm font-semibold text-cedar">
                    Evidence
                </summary>
                <div className="mt-3 grid gap-3">
                    {group.candidates.map((candidate) => (
                        <section
                            key={candidate.id}
                            className="rounded-md bg-white p-3"
                        >
                            <div className="flex flex-wrap items-center gap-2 font-dmSans text-caption text-soft-charcoal">
                                <span className="font-semibold text-cedar">
                                    {candidate.comedian.name}
                                </span>
                                <span>
                                    {formatPercent(candidate.confidence)}
                                </span>
                                {candidate.associationType && (
                                    <span>{candidate.associationType}</span>
                                )}
                                <span>{candidate.source}</span>
                            </div>
                            <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-soft-charcoal">
                                {evidencePreview(candidate.evidence)}
                            </pre>
                        </section>
                    ))}
                </div>
            </details>
        </AdminPodcastHostshipReviewGroupFrame>
    );
}
