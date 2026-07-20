import { ExternalLink, Save } from "lucide-react";
import { Button } from "@/ui/components/ui/button";
import { AdminPodcastHostshipAssignmentControls } from "./AdminPodcastHostshipAssignmentControls";
import { AdminPodcastHostshipReviewGroupFrame } from "./AdminPodcastHostshipReviewGroupFrame";
import type {
    ComedianOption,
    ComedianReviewGroup,
    PodcastReviewGroup,
} from "./AdminPodcastHostshipReviewModels";
import { formatPopularity } from "./AdminPodcastHostshipReviewModels";

type Props = {
    group: ComedianReviewGroup;
    selectedHosts: Record<string, ComedianOption | null>;
    selectedCohosts: Record<string, ComedianOption[]>;
    confirmedHostIds: Record<string, number | null>;
    manualFeedUrl: string;
    collapsed: boolean;
    busy: boolean;
    ingestDisabled: boolean;
    ingesting: boolean;
    onToggle: (groupKey: string) => void;
    onManualFeedUrlChange: (value: string) => void;
    onIngest: (group: ComedianReviewGroup) => void;
    onSelectHost: (groupKey: string, option: ComedianOption) => void;
    onRemoveHost: (groupKey: string) => void;
    onToggleCohost: (
        groupKey: string,
        option: ComedianOption,
        isCohost: boolean,
    ) => void;
    onSave: (group: PodcastReviewGroup) => void;
};

export function AdminPodcastHostshipComedianCard({
    group,
    selectedHosts,
    selectedCohosts,
    confirmedHostIds,
    manualFeedUrl,
    collapsed,
    busy,
    ingestDisabled,
    ingesting,
    onToggle,
    onManualFeedUrlChange,
    onIngest,
    onSelectHost,
    onRemoveHost,
    onToggleCohost,
    onSave,
}: Props) {
    const hostedPodcastCount = group.podcastGroups.filter(
        (podcastGroup) =>
            confirmedHostIds[podcastGroup.key] === group.comedian.id,
    ).length;
    const frameKey = `comedian-${group.key}`;
    const comedianOption: ComedianOption = {
        id: group.comedian.id,
        uuid: group.comedian.uuid,
        name: group.comedian.name,
        popularity: group.comedian.popularity,
    };

    return (
        <AdminPodcastHostshipReviewGroupFrame
            groupKey={frameKey}
            title={group.comedian.name}
            subtitle={`Popularity ${formatPopularity(group.popularity)}`}
            summary={`${hostedPodcastCount} hosted podcast${hostedPodcastCount === 1 ? "" : "s"}`}
            collapsed={collapsed}
            onToggle={onToggle}
        >
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                    <h2 className="font-urbanist-bold text-h3 leading-tight text-cedar">
                        {group.comedian.name}
                    </h2>
                    <p className="font-dmSans text-caption text-soft-charcoal">
                        Popularity {formatPopularity(group.popularity)} ·{" "}
                        {hostedPodcastCount} hosted podcast
                        {hostedPodcastCount === 1 ? "" : "s"}
                    </p>
                </div>
            </div>
            <div className="grid gap-2 rounded-md border border-gray-300 bg-white p-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                <label className="grid gap-1 font-dmSans text-sm font-semibold text-cedar">
                    Add arbitrary RSS feed
                    <input
                        type="url"
                        value={manualFeedUrl}
                        onChange={(event) =>
                            onManualFeedUrlChange(event.target.value)
                        }
                        className="min-w-0 rounded-md border border-gray-300 bg-white px-3 py-2 font-dmSans text-body font-normal text-foreground placeholder:text-soft-charcoal focus:border-copper-dark focus:outline-none focus:ring-2 focus:ring-copper-dark"
                        placeholder="https://example.com/rss.xml"
                    />
                </label>
                <Button
                    type="button"
                    variant="outline"
                    className="border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white disabled:border-gray-300 disabled:bg-gray-100 disabled:!text-soft-charcoal disabled:opacity-100"
                    disabled={ingestDisabled || !manualFeedUrl.trim()}
                    onClick={() => onIngest(group)}
                >
                    {ingesting ? "Ingesting..." : "Ingest RSS"}
                </Button>
            </div>
            <div className="grid gap-3">
                {group.podcastGroups.map((podcastGroup) => {
                    const selectedHost =
                        selectedHosts[podcastGroup.key] ?? null;
                    const isDenied = Boolean(
                        podcastGroup.podcast.denyListEntry,
                    );
                    const isSelectedHost =
                        selectedHost?.id === group.comedian.id;

                    return (
                        <section
                            key={podcastGroup.key}
                            className="grid gap-3 rounded-md border border-gray-200 bg-ecru-white p-3 md:grid-cols-[minmax(0,1fr)_auto]"
                        >
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <h3 className="font-urbanist-bold text-body text-cedar">
                                        {podcastGroup.podcast.title}
                                    </h3>
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
                                <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                                    {podcastGroup.podcast.authorName
                                        ? `by ${podcastGroup.podcast.authorName}`
                                        : "Author missing"}
                                </p>
                                <div className="mt-2 flex flex-wrap gap-3 font-dmSans text-caption">
                                    {podcastGroup.podcast.feedUrl ? (
                                        <a
                                            href={podcastGroup.podcast.feedUrl}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex max-w-full items-center gap-1 text-copper-dark hover:underline"
                                        >
                                            <span className="truncate">
                                                RSS:{" "}
                                                {podcastGroup.podcast.feedUrl}
                                            </span>
                                            <ExternalLink
                                                className="h-3.5 w-3.5 shrink-0"
                                                aria-hidden="true"
                                            />
                                        </a>
                                    ) : (
                                        <span className="text-soft-charcoal">
                                            RSS feed missing
                                        </span>
                                    )}
                                    {podcastGroup.podcast.websiteUrl && (
                                        <a
                                            href={
                                                podcastGroup.podcast.websiteUrl
                                            }
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex max-w-full items-center gap-1 text-copper-dark hover:underline"
                                        >
                                            <span className="truncate">
                                                Website:{" "}
                                                {
                                                    podcastGroup.podcast
                                                        .websiteUrl
                                                }
                                            </span>
                                            <ExternalLink
                                                className="h-3.5 w-3.5 shrink-0"
                                                aria-hidden="true"
                                            />
                                        </a>
                                    )}
                                </div>
                                <AdminPodcastHostshipAssignmentControls
                                    groupKey={podcastGroup.key}
                                    selectedHost={selectedHost}
                                    selectedCohosts={
                                        selectedCohosts[podcastGroup.key] ?? []
                                    }
                                    isDenied={isDenied}
                                    showCohosts={false}
                                    summaryClassName="mt-2 flex flex-wrap gap-2"
                                    onSelectHost={onSelectHost}
                                    onRemoveHost={onRemoveHost}
                                    onToggleCohost={onToggleCohost}
                                />
                            </div>
                            <div className="flex flex-wrap items-center gap-2 md:justify-end">
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="border-copper-dark bg-white !text-copper-dark hover:bg-copper-dark hover:!text-white"
                                    onClick={() =>
                                        onSelectHost(
                                            podcastGroup.key,
                                            comedianOption,
                                        )
                                    }
                                    disabled={busy || isSelectedHost}
                                >
                                    Set as host
                                </Button>
                                <Button
                                    type="button"
                                    className="gap-2 !text-white"
                                    variant="roundedShimmer"
                                    onClick={() => onSave(podcastGroup)}
                                    disabled={busy}
                                    aria-label={`Save ${podcastGroup.podcast.title}`}
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
        </AdminPodcastHostshipReviewGroupFrame>
    );
}
