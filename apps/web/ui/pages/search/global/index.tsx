"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Building2, CalendarDays, Mic2, Podcast, Search } from "lucide-react";
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
        });
        return `/api/v1/search?${params.toString()}`;
    }, [filter, trimmedQuery]);

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

                <div className="space-y-3" aria-live="polite">
                    {isLoading && trimmedQuery ? (
                        <p className="font-dmSans text-sm text-copper/70">
                            Searching...
                        </p>
                    ) : null}
                    {!trimmedQuery ? (
                        <p className="font-dmSans text-sm text-copper/70">
                            Start typing to search across LaughTrack.
                        </p>
                    ) : null}
                    {trimmedQuery && results.length === 0 && !isLoading ? (
                        <p className="font-dmSans text-sm text-copper/70">
                            No results found.
                        </p>
                    ) : null}
                    {results.map((result) => (
                        <SearchResultRow key={result.id} result={result} />
                    ))}
                </div>
            </section>
        </main>
    );
}
