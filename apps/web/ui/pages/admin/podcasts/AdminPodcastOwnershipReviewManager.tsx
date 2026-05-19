"use client";

import { ExternalLink, Plus, Save, Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/ui/components/ui/button";
import type { AdminPodcastOwnershipReviewCandidate } from "@/lib/admin/podcastOwnershipReviews";

export type { AdminPodcastOwnershipReviewCandidate };

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type OwnerOption = {
    id: number;
    uuid: string;
    name: string;
    popularity: number;
    confidence?: number;
    source?: string;
    associationType?: string | null;
};

type ReviewView = "podcast" | "comedian";
type ReviewSort =
    | "name-asc"
    | "name-desc"
    | "popularity-desc"
    | "popularity-asc";

type PodcastReviewGroup = {
    key: string;
    podcast: NonNullable<AdminPodcastOwnershipReviewCandidate["podcast"]>;
    candidates: AdminPodcastOwnershipReviewCandidate[];
    ownerOptions: OwnerOption[];
    initialOwner: OwnerOption | null;
    popularity: number;
};

type ComedianReviewGroup = {
    key: string;
    comedian: AdminPodcastOwnershipReviewCandidate["comedian"];
    candidates: AdminPodcastOwnershipReviewCandidate[];
    podcastGroups: PodcastReviewGroup[];
    popularity: number;
};

type SearchResult = {
    id: number;
    uuid: string;
    name: string;
    popularity?: number;
};

type Props = {
    candidates: AdminPodcastOwnershipReviewCandidate[];
};

function formatPercent(value: number) {
    return `${Math.round(value * 100)}%`;
}

function formatDate(iso: string) {
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function evidencePreview(evidence: unknown) {
    if (!evidence || typeof evidence !== "object") return "No evidence";
    return JSON.stringify(evidence, null, 2);
}

function groupCandidates(
    candidates: AdminPodcastOwnershipReviewCandidate[],
): PodcastReviewGroup[] {
    const byPodcast = new Map<number, AdminPodcastOwnershipReviewCandidate[]>();
    for (const candidate of candidates) {
        if (!candidate.podcast) continue;
        const rows = byPodcast.get(candidate.podcast.id) ?? [];
        rows.push(candidate);
        byPodcast.set(candidate.podcast.id, rows);
    }

    return Array.from(byPodcast.entries()).map(([podcastId, rows]) => {
        const podcast = rows[0].podcast!;
        const ownershipOptions = rows.flatMap((candidate) =>
            candidate.existingOwnerships.map((ownership) => ({
                id: ownership.comedian.id,
                uuid: ownership.comedian.uuid,
                name: ownership.comedian.name,
                popularity: ownership.comedian.popularity,
                confidence: ownership.confidence,
                source: ownership.source,
                associationType: ownership.associationType,
                reviewStatus: ownership.reviewStatus,
            })),
        );
        const candidateOptions = rows.map((candidate) => ({
            id: candidate.comedian.id,
            uuid: candidate.comedian.uuid,
            name: candidate.comedian.name,
            popularity: candidate.comedian.popularity,
            confidence: candidate.confidence,
            source: candidate.source,
            associationType: candidate.associationType,
        }));
        const uniqueOptions = new Map<number, OwnerOption>();
        for (const option of [...ownershipOptions, ...candidateOptions]) {
            if (!uniqueOptions.has(option.id))
                uniqueOptions.set(option.id, option);
        }
        const acceptedOwner = ownershipOptions.find(
            (option) => option.reviewStatus === "accepted",
        );

        return {
            key: String(podcastId),
            podcast,
            candidates: rows,
            ownerOptions: Array.from(uniqueOptions.values()),
            initialOwner: acceptedOwner ?? candidateOptions[0] ?? null,
            popularity: Math.max(
                0,
                ...rows.map((candidate) => candidate.comedian.popularity),
                ...ownershipOptions.map((option) => option.popularity),
            ),
        };
    });
}

function groupByComedian(
    candidates: AdminPodcastOwnershipReviewCandidate[],
    podcastGroups: PodcastReviewGroup[],
): ComedianReviewGroup[] {
    const podcastGroupById = new Map(
        podcastGroups.map((group) => [group.podcast.id, group]),
    );
    const byComedian = new Map<
        number,
        AdminPodcastOwnershipReviewCandidate[]
    >();
    for (const candidate of candidates) {
        if (!candidate.podcast) continue;
        const rows = byComedian.get(candidate.comedian.id) ?? [];
        rows.push(candidate);
        byComedian.set(candidate.comedian.id, rows);
    }

    return Array.from(byComedian.entries()).map(([comedianId, rows]) => {
        const comedian = rows[0].comedian;
        const linkedGroups = rows
            .map((candidate) =>
                candidate.podcast
                    ? podcastGroupById.get(candidate.podcast.id)
                    : undefined,
            )
            .filter((group): group is PodcastReviewGroup => Boolean(group));
        return {
            key: String(comedianId),
            comedian,
            candidates: rows,
            podcastGroups: Array.from(
                new Map(
                    linkedGroups.map((group) => [group.key, group]),
                ).values(),
            ),
            popularity: comedian.popularity,
        };
    });
}

function compareText(a: string, b: string) {
    return a.localeCompare(b, undefined, { sensitivity: "base" });
}

function sortPodcastGroups(groups: PodcastReviewGroup[], sort: ReviewSort) {
    return [...groups].sort((a, b) => {
        switch (sort) {
            case "name-desc":
                return compareText(b.podcast.title, a.podcast.title);
            case "popularity-desc":
                return (
                    b.popularity - a.popularity ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "popularity-asc":
                return (
                    a.popularity - b.popularity ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "name-asc":
            default:
                return compareText(a.podcast.title, b.podcast.title);
        }
    });
}

function sortComedianGroups(groups: ComedianReviewGroup[], sort: ReviewSort) {
    return [...groups].sort((a, b) => {
        switch (sort) {
            case "name-desc":
                return compareText(b.comedian.name, a.comedian.name);
            case "popularity-desc":
                return (
                    b.popularity - a.popularity ||
                    compareText(a.comedian.name, b.comedian.name)
                );
            case "popularity-asc":
                return (
                    a.popularity - b.popularity ||
                    compareText(a.comedian.name, b.comedian.name)
                );
            case "name-asc":
            default:
                return compareText(a.comedian.name, b.comedian.name);
        }
    });
}

function selectedOwnerDefaults(groups: PodcastReviewGroup[]) {
    return Object.fromEntries(
        groups.map((group) => [group.key, group.initialOwner]),
    ) as Record<string, OwnerOption | null>;
}

export default function AdminPodcastOwnershipReviewManager({
    candidates,
}: Props) {
    const router = useRouter();
    const groups = groupCandidates(candidates);
    const comedianGroups = groupByComedian(candidates, groups);
    const [activeView, setActiveView] = useState<ReviewView>("podcast");
    const [sort, setSort] = useState<ReviewSort>("name-asc");
    const [selectedOwners, setSelectedOwners] = useState<
        Record<string, OwnerOption | null>
    >(() => selectedOwnerDefaults(groups));
    const [notes, setNotes] = useState<Record<string, string>>({});
    const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
    const [searchResults, setSearchResults] = useState<
        Record<string, SearchResult[]>
    >({});
    const [searchingKey, setSearchingKey] = useState<string | null>(null);
    const [pendingKey, setPendingKey] = useState<string | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isPending, startTransition] = useTransition();

    async function searchComedians(groupKey: string) {
        const term = searchTerms[groupKey]?.trim();
        if (!term) {
            setSearchResults((prev) => ({ ...prev, [groupKey]: [] }));
            return;
        }

        setSearchingKey(groupKey);
        setStatus({ kind: "idle" });
        try {
            const params = new URLSearchParams({
                comedian: term,
                includeEmpty: "true",
                size: "6",
            });
            const res = await fetch(`/api/v1/comedians/search?${params}`);
            if (!res.ok) throw new Error(`Search failed (${res.status})`);
            const body = (await res.json()) as { data?: SearchResult[] };
            setSearchResults((prev) => ({
                ...prev,
                [groupKey]: (body.data ?? []).map((result) => ({
                    ...result,
                    popularity: result.popularity ?? 0,
                })),
            }));
        } catch (error) {
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Search failed",
            });
        } finally {
            setSearchingKey(null);
        }
    }

    async function save(group: PodcastReviewGroup) {
        const reason = notes[group.key]?.trim() ?? "";
        const owner = selectedOwners[group.key] ?? null;
        setStatus({ kind: "idle" });
        setPendingKey(group.key);

        let res: Response;
        try {
            res = await fetch("/api/admin/podcast-ownership-reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    podcastId: group.podcast.id,
                    ownerComedianId: owner?.id ?? null,
                    reason,
                }),
            });
        } catch (error) {
            setPendingKey(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingKey(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        setStatus({
            kind: "ok",
            message:
                owner === null
                    ? `${group.podcast.title} blocked.`
                    : `${group.podcast.title} approved with ${owner.name} as owner.`,
        });
        startTransition(() => router.refresh());
    }

    if (groups.length === 0) {
        return (
            <div className="rounded-md border border-copper/25 bg-white p-6 font-dmSans text-body text-soft-charcoal">
                No pending podcast ownership reviews.
            </div>
        );
    }

    const sortedPodcastGroups = sortPodcastGroups(groups, sort);
    const sortedComedianGroups = sortComedianGroups(comedianGroups, sort);

    return (
        <div className="space-y-5">
            {status.kind === "ok" && (
                <p className="rounded-md border border-green-200 bg-green-50 px-4 py-3 font-dmSans text-sm text-green-800">
                    {status.message}
                </p>
            )}
            {status.kind === "error" && (
                <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 font-dmSans text-sm text-red-800">
                    {status.message}
                </p>
            )}
            <div className="flex flex-col gap-3 rounded-md border border-gray-300 bg-white p-3 md:flex-row md:items-center md:justify-between">
                <div
                    className="inline-flex w-fit overflow-hidden rounded-md border border-gray-300"
                    aria-label="Review view"
                >
                    <button
                        type="button"
                        onClick={() => setActiveView("podcast")}
                        className={`px-3 py-2 font-dmSans text-sm font-semibold ${
                            activeView === "podcast"
                                ? "bg-copper-dark text-white"
                                : "bg-white text-cedar hover:bg-ecru-white"
                        }`}
                    >
                        By podcast
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveView("comedian")}
                        className={`border-l border-gray-300 px-3 py-2 font-dmSans text-sm font-semibold ${
                            activeView === "comedian"
                                ? "bg-copper-dark text-white"
                                : "bg-white text-cedar hover:bg-ecru-white"
                        }`}
                    >
                        By comedian
                    </button>
                </div>
                <label className="flex w-full max-w-sm items-center gap-2 font-dmSans text-sm font-semibold text-cedar md:justify-end">
                    Sort
                    <select
                        value={sort}
                        onChange={(event) =>
                            setSort(event.target.value as ReviewSort)
                        }
                        className="min-w-0 flex-1 rounded-md border border-gray-300 bg-white px-3 py-2 font-dmSans text-sm font-normal text-foreground focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark md:flex-none"
                    >
                        <option value="name-asc">Name A-Z</option>
                        <option value="name-desc">Name Z-A</option>
                        <option value="popularity-desc">
                            Popularity high-low
                        </option>
                        <option value="popularity-asc">
                            Popularity low-high
                        </option>
                    </select>
                </label>
            </div>
            <ul className="divide-y divide-gray-300 rounded-md border border-gray-300 bg-white">
                {activeView === "podcast"
                    ? sortedPodcastGroups.map((group) => {
                          const noteId = `podcast-review-note-${group.key}`;
                          const searchId = `podcast-owner-search-${group.key}`;
                          const selectedOwner =
                              selectedOwners[group.key] ?? null;
                          const disabled = isPending || pendingKey !== null;
                          const resultRows = searchResults[group.key] ?? [];
                          return (
                              <li key={group.key} className="grid gap-4 p-4">
                                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
                                      <div className="min-w-0">
                                          <div className="flex flex-wrap items-center gap-2">
                                              <h2 className="font-gilroy-bold text-h3 leading-tight text-cedar">
                                                  {group.podcast.title}
                                              </h2>
                                              <span
                                                  className={`rounded-md px-2 py-1 font-dmSans text-caption font-semibold ${
                                                      selectedOwner
                                                          ? "bg-green-50 text-green-800"
                                                          : "bg-red-50 text-red-800"
                                                  }`}
                                              >
                                                  {selectedOwner
                                                      ? "Approved"
                                                      : "Blocked"}
                                              </span>
                                          </div>
                                          <div className="mt-2 font-dmSans text-body text-soft-charcoal">
                                              {group.podcast.authorName && (
                                                  <span>
                                                      by{" "}
                                                      {group.podcast.authorName}
                                                  </span>
                                              )}
                                          </div>
                                          <div className="mt-3 flex flex-wrap gap-2">
                                              {selectedOwner ? (
                                                  <span className="inline-flex items-center gap-2 rounded-md border border-green-300 bg-green-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-green-900">
                                                      Owner:{" "}
                                                      {selectedOwner.name}
                                                      <button
                                                          type="button"
                                                          onClick={() =>
                                                              setSelectedOwners(
                                                                  (prev) => ({
                                                                      ...prev,
                                                                      [group.key]:
                                                                          null,
                                                                  }),
                                                              )
                                                          }
                                                          className="rounded-full p-0.5 text-green-900 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-700"
                                                          aria-label={`Remove ${selectedOwner.name} as owner`}
                                                      >
                                                          <X
                                                              className="h-3.5 w-3.5"
                                                              aria-hidden="true"
                                                          />
                                                      </button>
                                                  </span>
                                              ) : (
                                                  <span className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-red-900">
                                                      No owner
                                                  </span>
                                              )}
                                          </div>
                                          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-caption text-soft-charcoal">
                                              <span>
                                                  {group.candidates.length}{" "}
                                                  candidate
                                                  {group.candidates.length === 1
                                                      ? ""
                                                      : "s"}
                                              </span>
                                              <span>
                                                  {group.podcast.feedUrl ??
                                                      group.candidates[0]
                                                          .sourcePodcastId}
                                              </span>
                                              <time
                                                  dateTime={
                                                      group.candidates[0]
                                                          .createdAt
                                                  }
                                              >
                                                  {formatDate(
                                                      group.candidates[0]
                                                          .createdAt,
                                                  )}
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
                                                      href={
                                                          group.podcast
                                                              .websiteUrl
                                                      }
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

                                      <div className="grid gap-3">
                                          <div className="grid gap-2">
                                              <p className="font-dmSans text-sm font-semibold text-cedar">
                                                  Owner candidates
                                              </p>
                                              <div className="flex flex-wrap gap-2">
                                                  {group.ownerOptions.map(
                                                      (option) => (
                                                          <button
                                                              key={option.id}
                                                              type="button"
                                                              onClick={() =>
                                                                  setSelectedOwners(
                                                                      (
                                                                          prev,
                                                                      ) => ({
                                                                          ...prev,
                                                                          [group.key]:
                                                                              option,
                                                                      }),
                                                                  )
                                                              }
                                                              className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 font-dmSans text-sm font-semibold ${
                                                                  selectedOwner?.id ===
                                                                  option.id
                                                                      ? "border-green-500 bg-green-50 text-green-900"
                                                                      : "border-gray-300 bg-white text-cedar hover:border-copper-dark"
                                                              }`}
                                                          >
                                                              <Plus
                                                                  className="h-3.5 w-3.5"
                                                                  aria-hidden="true"
                                                              />
                                                              {option.name}
                                                              {option.confidence !==
                                                                  undefined && (
                                                                  <span className="font-normal text-soft-charcoal">
                                                                      {formatPercent(
                                                                          option.confidence,
                                                                      )}
                                                                  </span>
                                                              )}
                                                          </button>
                                                      ),
                                                  )}
                                              </div>
                                          </div>
                                          <div className="grid gap-1">
                                              <label
                                                  htmlFor={searchId}
                                                  className="font-dmSans text-sm font-semibold text-cedar"
                                              >
                                                  Add owner
                                              </label>
                                              <div className="flex gap-2">
                                                  <input
                                                      id={searchId}
                                                      value={
                                                          searchTerms[
                                                              group.key
                                                          ] ?? ""
                                                      }
                                                      onChange={(event) =>
                                                          setSearchTerms(
                                                              (prev) => ({
                                                                  ...prev,
                                                                  [group.key]:
                                                                      event
                                                                          .target
                                                                          .value,
                                                              }),
                                                          )
                                                      }
                                                      className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 font-dmSans text-body font-normal text-foreground focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark"
                                                  />
                                                  <Button
                                                      type="button"
                                                      variant="outline"
                                                      className="gap-2 border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper-dark focus-visible:ring-0"
                                                      onClick={() =>
                                                          void searchComedians(
                                                              group.key,
                                                          )
                                                      }
                                                      disabled={
                                                          disabled ||
                                                          searchingKey ===
                                                              group.key
                                                      }
                                                  >
                                                      <Search
                                                          className="h-4 w-4"
                                                          aria-hidden="true"
                                                      />
                                                      Search
                                                  </Button>
                                              </div>
                                          </div>
                                          {resultRows.length > 0 && (
                                              <div className="flex flex-wrap gap-2">
                                                  {resultRows.map((result) => (
                                                      <button
                                                          key={result.id}
                                                          type="button"
                                                          onClick={() =>
                                                              setSelectedOwners(
                                                                  (prev) => ({
                                                                      ...prev,
                                                                      [group.key]:
                                                                          {
                                                                              ...result,
                                                                              popularity:
                                                                                  result.popularity ??
                                                                                  0,
                                                                          },
                                                                  }),
                                                              )
                                                          }
                                                          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 font-dmSans text-sm font-semibold text-cedar hover:border-copper-dark"
                                                      >
                                                          {result.name}
                                                      </button>
                                                  ))}
                                              </div>
                                          )}
                                          <label
                                              htmlFor={noteId}
                                              className="grid gap-1 font-dmSans text-sm font-semibold text-cedar"
                                          >
                                              Review note
                                              <textarea
                                                  id={noteId}
                                                  value={notes[group.key] ?? ""}
                                                  onChange={(event) =>
                                                      setNotes((prev) => ({
                                                          ...prev,
                                                          [group.key]:
                                                              event.target
                                                                  .value,
                                                      }))
                                                  }
                                                  className="min-h-20 rounded-md border border-gray-300 px-3 py-2 font-dmSans text-body font-normal text-foreground focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark"
                                                  maxLength={1000}
                                              />
                                          </label>
                                          <div>
                                              <Button
                                                  type="button"
                                                  className="gap-2 !text-white"
                                                  variant="roundedShimmer"
                                                  onClick={() =>
                                                      void save(group)
                                                  }
                                                  disabled={disabled}
                                                  aria-label={`Save ${group.podcast.title}`}
                                              >
                                                  <Save
                                                      className="h-4 w-4"
                                                      aria-hidden="true"
                                                  />
                                                  Save
                                              </Button>
                                          </div>
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
                                                          {
                                                              candidate.comedian
                                                                  .name
                                                          }
                                                      </span>
                                                      <span>
                                                          {formatPercent(
                                                              candidate.confidence,
                                                          )}
                                                      </span>
                                                      {candidate.associationType && (
                                                          <span>
                                                              {
                                                                  candidate.associationType
                                                              }
                                                          </span>
                                                      )}
                                                      <span>
                                                          {candidate.source}
                                                      </span>
                                                  </div>
                                                  <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-soft-charcoal">
                                                      {evidencePreview(
                                                          candidate.evidence,
                                                      )}
                                                  </pre>
                                              </section>
                                          ))}
                                      </div>
                                  </details>
                              </li>
                          );
                      })
                    : sortedComedianGroups.map((comedianGroup) => (
                          <li
                              key={comedianGroup.key}
                              className="grid gap-4 p-4"
                          >
                              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                                  <div>
                                      <h2 className="font-gilroy-bold text-h3 leading-tight text-cedar">
                                          {comedianGroup.comedian.name}
                                      </h2>
                                      <p className="font-dmSans text-caption text-soft-charcoal">
                                          Popularity{" "}
                                          {comedianGroup.popularity.toFixed(1)}{" "}
                                          · {comedianGroup.podcastGroups.length}{" "}
                                          podcast
                                          {comedianGroup.podcastGroups
                                              .length === 1
                                              ? ""
                                              : "s"}{" "}
                                          attached
                                      </p>
                                  </div>
                              </div>
                              <div className="grid gap-3">
                                  {comedianGroup.podcastGroups.map((group) => {
                                      const selectedOwner =
                                          selectedOwners[group.key] ?? null;
                                      const isSelectedOwner =
                                          selectedOwner?.id ===
                                          comedianGroup.comedian.id;
                                      const disabled =
                                          isPending || pendingKey !== null;
                                      return (
                                          <section
                                              key={group.key}
                                              className="grid gap-3 rounded-md border border-gray-200 bg-ecru-white p-3 md:grid-cols-[minmax(0,1fr)_auto]"
                                          >
                                              <div className="min-w-0">
                                                  <div className="flex flex-wrap items-center gap-2">
                                                      <h3 className="font-gilroy-bold text-body text-cedar">
                                                          {group.podcast.title}
                                                      </h3>
                                                      <span
                                                          className={`rounded-md px-2 py-1 font-dmSans text-caption font-semibold ${
                                                              selectedOwner
                                                                  ? "bg-green-50 text-green-800"
                                                                  : "bg-red-50 text-red-800"
                                                          }`}
                                                      >
                                                          {selectedOwner
                                                              ? "Approved"
                                                              : "Blocked"}
                                                      </span>
                                                  </div>
                                                  <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                                                      {group.podcast.authorName
                                                          ? `by ${group.podcast.authorName}`
                                                          : "Author missing"}
                                                  </p>
                                                  <div className="mt-2 flex flex-wrap gap-2">
                                                      {selectedOwner ? (
                                                          <span className="inline-flex items-center gap-2 rounded-md border border-green-300 bg-green-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-green-900">
                                                              Owner:{" "}
                                                              {
                                                                  selectedOwner.name
                                                              }
                                                              <button
                                                                  type="button"
                                                                  onClick={() =>
                                                                      setSelectedOwners(
                                                                          (
                                                                              prev,
                                                                          ) => ({
                                                                              ...prev,
                                                                              [group.key]:
                                                                                  null,
                                                                          }),
                                                                      )
                                                                  }
                                                                  className="rounded-full p-0.5 text-green-900 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-700"
                                                                  aria-label={`Remove ${selectedOwner.name} as owner`}
                                                              >
                                                                  <X
                                                                      className="h-3.5 w-3.5"
                                                                      aria-hidden="true"
                                                                  />
                                                              </button>
                                                          </span>
                                                      ) : (
                                                          <span className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-red-900">
                                                              No owner
                                                          </span>
                                                      )}
                                                  </div>
                                              </div>
                                              <div className="flex flex-wrap items-center gap-2 md:justify-end">
                                                  <Button
                                                      type="button"
                                                      variant="outline"
                                                      className="border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white"
                                                      onClick={() =>
                                                          setSelectedOwners(
                                                              (prev) => ({
                                                                  ...prev,
                                                                  [group.key]: {
                                                                      id: comedianGroup
                                                                          .comedian
                                                                          .id,
                                                                      uuid: comedianGroup
                                                                          .comedian
                                                                          .uuid,
                                                                      name: comedianGroup
                                                                          .comedian
                                                                          .name,
                                                                      popularity:
                                                                          comedianGroup
                                                                              .comedian
                                                                              .popularity,
                                                                  },
                                                              }),
                                                          )
                                                      }
                                                      disabled={
                                                          disabled ||
                                                          isSelectedOwner
                                                      }
                                                  >
                                                      Set as owner
                                                  </Button>
                                                  <Button
                                                      type="button"
                                                      className="gap-2 !text-white"
                                                      variant="roundedShimmer"
                                                      onClick={() =>
                                                          void save(group)
                                                      }
                                                      disabled={disabled}
                                                      aria-label={`Save ${group.podcast.title}`}
                                                  >
                                                      <Save
                                                          className="h-4 w-4"
                                                          aria-hidden="true"
                                                      />
                                                      Save
                                                  </Button>
                                              </div>
                                          </section>
                                      );
                                  })}
                              </div>
                          </li>
                      ))}
            </ul>
        </div>
    );
}
