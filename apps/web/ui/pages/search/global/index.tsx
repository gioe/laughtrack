"use client";

// /search is the cross-entity typeahead surface — a quick disambiguator for
// users who know what they're looking for. Per-entity collection pages
// (/show/search, /comedian/search, /club/search, /podcast/search) own the
// rich filter chrome and browse experience. This page caps each entity group
// at TYPEAHEAD_GROUP_LIMIT and offers a "See all" escape hatch that hands the
// query off to the entity's collection page.

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
    ArrowRight,
    Building2,
    CalendarDays,
    Mic2,
    Podcast,
    Search,
} from "lucide-react";
import EntityCard from "@/ui/components/cards/entity";

const ENTITY_FILTERS = [
    { id: "all", label: "All" },
    { id: "show", label: "Shows" },
    { id: "comedian", label: "Comedians" },
    { id: "club", label: "Clubs" },
    { id: "podcast", label: "Podcasts" },
] as const;

type SearchEntityType = Exclude<(typeof ENTITY_FILTERS)[number]["id"], "all">;
type SearchFilter = (typeof ENTITY_FILTERS)[number]["id"];

// How many matches each entity group shows before the "See all" link
// hands users off to the per-entity collection page.
const TYPEAHEAD_GROUP_LIMIT = 5;

const ENTITY_GROUP_ORDER: SearchEntityType[] = [
    "show",
    "comedian",
    "club",
    "podcast",
];

const ENTITY_COLLECTION_PATH: Record<SearchEntityType, string> = {
    show: "/show/search",
    comedian: "/comedian/search",
    club: "/club/search",
    podcast: "/podcast/search",
};

const ENTITY_GROUP_HEADING: Record<SearchEntityType, string> = {
    show: "Shows",
    comedian: "Comedians",
    club: "Clubs",
    podcast: "Podcasts",
};

type GlobalSearchResult = {
    id: string;
    entityType: SearchEntityType;
    title: string;
    subtitle: string | null;
    href: string;
    imageUrl: string | null;
};

type GlobalSearchResponse = {
    data: GlobalSearchResult[];
    total: number;
    totals: Record<SearchFilter, number>;
};

const ENTITY_META = {
    show: {
        label: "Show",
        icon: CalendarDays,
    },
    comedian: {
        label: "Comedian",
        icon: Mic2,
    },
    club: {
        label: "Club",
        icon: Building2,
    },
    podcast: {
        label: "Podcast",
        icon: Podcast,
    },
} as const;

function getEntityLabel(type: SearchEntityType) {
    return ENTITY_META[type].label;
}

function ResultArtwork({ result }: { result: GlobalSearchResult }) {
    const Icon = ENTITY_META[result.entityType].icon;
    return (
        <span className="relative flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-lg bg-muted text-muted-foreground">
            {result.imageUrl ? (
                <Image
                    src={result.imageUrl}
                    alt=""
                    fill
                    sizes="48px"
                    className="object-cover"
                />
            ) : (
                <Icon size={22} aria-hidden="true" />
            )}
        </span>
    );
}

function SearchResultRow({ result }: { result: GlobalSearchResult }) {
    const entityLabel = getEntityLabel(result.entityType);
    const external = result.href.startsWith("http");
    const row = (
        <EntityCard
            as="article"
            chrome="warm"
            ariaLabel={`${result.title} ${result.entityType}`}
            className="flex items-start gap-3 p-4"
            disableHover
        >
            <ResultArtwork result={result} />
            <span className="min-w-0 flex-1">
                <span className="block font-gilroy-bold text-body font-bold leading-tight text-foreground line-clamp-2 group-hover:text-copper">
                    {result.title}
                </span>
                <span className="mt-0.5 block font-dmSans text-xs leading-snug text-gray-500 line-clamp-2">
                    {result.subtitle || entityLabel}
                </span>
                <span className="mt-2 inline-flex rounded-full bg-copper/10 px-2 py-0.5 font-dmSans text-caption font-semibold text-copper">
                    {entityLabel}
                </span>
            </span>
        </EntityCard>
    );

    const linkClassName =
        "group block rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper";

    if (external) {
        return (
            <a
                href={result.href}
                target="_blank"
                rel="noopener noreferrer"
                className={linkClassName}
                aria-label={`${result.title} ${result.entityType}`}
            >
                {row}
            </a>
        );
    }

    return (
        <Link
            href={result.href}
            className={linkClassName}
            aria-label={`${result.title} ${result.entityType}`}
        >
            {row}
        </Link>
    );
}

export default function GlobalSearchClient() {
    const [query, setQuery] = useState("");
    const [filter, setFilter] = useState<SearchFilter>("all");
    const [results, setResults] = useState<GlobalSearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [totals, setTotals] = useState<GlobalSearchResponse["totals"]>({
        all: 0,
        show: 0,
        comedian: 0,
        club: 0,
        podcast: 0,
    });
    const [error, setError] = useState<string | null>(null);

    const trimmedQuery = query.trim();
    const requestPath = useMemo(() => {
        if (!trimmedQuery) return null;
        const params = new URLSearchParams({
            q: trimmedQuery,
            type: filter,
            // Request enough rows that each entity group can hit
            // TYPEAHEAD_GROUP_LIMIT under "All". The API caps at 25.
            limit: String(TYPEAHEAD_GROUP_LIMIT * 4),
        });
        return `/api/v1/search?${params.toString()}`;
    }, [filter, trimmedQuery]);

    const groupedResults = useMemo(() => {
        const groups: Record<SearchEntityType, GlobalSearchResult[]> = {
            show: [],
            comedian: [],
            club: [],
            podcast: [],
        };
        for (const result of results) {
            groups[result.entityType].push(result);
        }
        return groups;
    }, [results]);

    const visibleGroupOrder = useMemo<SearchEntityType[]>(() => {
        if (filter !== "all") return [filter];
        return ENTITY_GROUP_ORDER.filter((t) => groupedResults[t].length > 0);
    }, [filter, groupedResults]);

    useEffect(() => {
        if (!requestPath) {
            setResults([]);
            setTotals({ all: 0, show: 0, comedian: 0, club: 0, podcast: 0 });
            setError(null);
            setIsLoading(false);
            return;
        }

        const controller = new AbortController();
        setIsLoading(true);
        void fetch(requestPath, { signal: controller.signal })
            .then((response) => {
                if (!response.ok) throw new Error(`${response.status}`);
                return response.json() as Promise<GlobalSearchResponse>;
            })
            .then((payload) => {
                setResults(payload.data);
                setTotals(payload.totals);
                setError(null);
            })
            .catch((err) => {
                if (err instanceof Error && err.name === "AbortError") {
                    return;
                }
                setError("Search failed");
                setResults([]);
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            });

        return () => controller.abort();
    }, [requestPath]);

    return (
        <main className="min-h-screen bg-coconut-cream">
            <section className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-8 sm:px-6 lg:px-8">
                <header>
                    <h1 className="font-gilroy-bold text-h1 font-bold text-foreground">
                        Search LaughTrack
                    </h1>
                </header>

                <div className="flex flex-col gap-3">
                    <label className="relative block">
                        <span className="sr-only">Search LaughTrack</span>
                        <Search
                            aria-hidden="true"
                            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-copper/60"
                            size={20}
                        />
                        <input
                            aria-label="Search LaughTrack"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            className="h-12 w-full rounded-lg border border-copper/20 bg-white pl-10 pr-4 font-dmSans text-body text-foreground outline-none transition focus:border-copper focus:ring-2 focus:ring-copper/20"
                            placeholder="Search shows, comedians, clubs, podcasts"
                        />
                    </label>

                    <div
                        className="flex flex-wrap gap-2"
                        aria-label="Search entity type"
                    >
                        {ENTITY_FILTERS.map((item) => {
                            const selected = filter === item.id;
                            const count = totals[item.id] ?? 0;
                            return (
                                <button
                                    key={item.id}
                                    type="button"
                                    onClick={() => setFilter(item.id)}
                                    aria-pressed={selected}
                                    className={`rounded-md border px-3 py-2 font-dmSans text-sm font-semibold transition ${
                                        selected
                                            ? "border-copper bg-copper text-white"
                                            : "border-copper/20 bg-white text-copper hover:border-copper/50"
                                    }`}
                                >
                                    {item.label}
                                    {count > 0 ? (
                                        <span className="ml-1 opacity-75">
                                            {count}
                                        </span>
                                    ) : null}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {error ? (
                    <p className="font-dmSans text-sm text-red-700">{error}</p>
                ) : null}

                <div className="space-y-6" aria-live="polite">
                    {isLoading && trimmedQuery ? (
                        <p className="font-dmSans text-sm text-copper/70">
                            Searching...
                        </p>
                    ) : null}
                    {!trimmedQuery ? (
                        <div className="space-y-4">
                            <p className="font-dmSans text-sm text-copper/70">
                                Start typing to jump to a show, comedian, club,
                                or podcast — or browse a category below.
                            </p>
                            <div
                                className="grid gap-3 sm:grid-cols-2"
                                role="navigation"
                                aria-label="Browse by category"
                            >
                                {ENTITY_GROUP_ORDER.map((entityType) => {
                                    const Icon = ENTITY_META[entityType].icon;
                                    return (
                                        <Link
                                            key={entityType}
                                            href={
                                                ENTITY_COLLECTION_PATH[
                                                    entityType
                                                ]
                                            }
                                            className="group flex items-center gap-3 rounded-lg border border-copper/20 bg-white px-4 py-3 transition hover:border-copper/50 hover:bg-copper/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                        >
                                            <span className="flex h-10 w-10 flex-none items-center justify-center rounded-md bg-copper/10 text-copper">
                                                <Icon
                                                    size={20}
                                                    aria-hidden="true"
                                                />
                                            </span>
                                            <span className="flex flex-col">
                                                <span className="font-gilroy-bold text-body font-bold text-foreground group-hover:text-copper">
                                                    Browse{" "}
                                                    {ENTITY_GROUP_HEADING[
                                                        entityType
                                                    ].toLowerCase()}
                                                </span>
                                                <span className="font-dmSans text-xs text-copper/60">
                                                    {entityType === "show"
                                                        ? "Upcoming dates, venues, and lineups"
                                                        : entityType ===
                                                            "comedian"
                                                          ? "Comedians on tour"
                                                          : entityType ===
                                                              "club"
                                                            ? "Comedy clubs and venues"
                                                            : "Comedy podcasts"}
                                                </span>
                                            </span>
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>
                    ) : null}
                    {trimmedQuery && results.length === 0 && !isLoading ? (
                        <p className="font-dmSans text-sm text-copper/70">
                            No results found.
                        </p>
                    ) : null}
                    {visibleGroupOrder.map((entityType) => {
                        const groupRows = groupedResults[entityType];
                        if (groupRows.length === 0) return null;
                        const groupTotal = totals[entityType] ?? 0;
                        const visible = groupRows.slice(
                            0,
                            TYPEAHEAD_GROUP_LIMIT,
                        );
                        const hasMore = groupTotal > visible.length;
                        const seeAllHref = `${ENTITY_COLLECTION_PATH[entityType]}?q=${encodeURIComponent(trimmedQuery)}`;
                        return (
                            <section
                                key={entityType}
                                aria-label={ENTITY_GROUP_HEADING[entityType]}
                                className="space-y-2"
                            >
                                <header className="flex items-baseline justify-between">
                                    <h2 className="font-gilroy-bold text-sm font-bold uppercase tracking-widest text-copper/70">
                                        {ENTITY_GROUP_HEADING[entityType]}
                                    </h2>
                                    {groupTotal > 0 ? (
                                        <span className="font-dmSans text-xs text-copper/60">
                                            {groupTotal.toLocaleString("en-US")}{" "}
                                            {groupTotal === 1
                                                ? "match"
                                                : "matches"}
                                        </span>
                                    ) : null}
                                </header>
                                <div className="space-y-2">
                                    {visible.map((result) => (
                                        <SearchResultRow
                                            key={result.id}
                                            result={result}
                                        />
                                    ))}
                                </div>
                                {hasMore ? (
                                    <Link
                                        href={seeAllHref}
                                        className="inline-flex items-center gap-1 font-dmSans text-sm font-semibold text-copper hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                    >
                                        See all{" "}
                                        {groupTotal.toLocaleString("en-US")}{" "}
                                        {ENTITY_GROUP_HEADING[
                                            entityType
                                        ].toLowerCase()}
                                        <ArrowRight
                                            size={14}
                                            aria-hidden="true"
                                        />
                                    </Link>
                                ) : null}
                            </section>
                        );
                    })}
                </div>
            </section>
        </main>
    );
}
