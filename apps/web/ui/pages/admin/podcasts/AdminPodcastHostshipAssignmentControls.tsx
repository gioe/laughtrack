import { Plus, X } from "lucide-react";
import type { ComedianOption } from "./AdminPodcastHostshipReviewModels";
import {
    formatAssociationType,
    formatPercent,
} from "./AdminPodcastHostshipReviewModels";

type Props = {
    groupKey: string;
    selectedHost: ComedianOption | null;
    selectedCohosts: ComedianOption[];
    isDenied: boolean;
    options?: ComedianOption[];
    showSummary?: boolean;
    showCohosts?: boolean;
    summaryClassName?: string;
    onSelectHost: (groupKey: string, option: ComedianOption) => void;
    onRemoveHost: (groupKey: string) => void;
    onToggleCohost: (
        groupKey: string,
        option: ComedianOption,
        isCohost: boolean,
    ) => void;
};

export function AdminPodcastHostshipAssignmentControls({
    groupKey,
    selectedHost,
    selectedCohosts,
    isDenied,
    options,
    showSummary = true,
    showCohosts = true,
    summaryClassName = "mt-3 flex flex-wrap gap-2",
    onSelectHost,
    onRemoveHost,
    onToggleCohost,
}: Props) {
    return (
        <>
            {showSummary && (
                <div className={summaryClassName}>
                    {selectedHost ? (
                        <span className="inline-flex items-center gap-2 rounded-md border border-green-300 bg-green-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-green-900">
                            Host: {selectedHost.name}
                            <button
                                type="button"
                                onClick={() => onRemoveHost(groupKey)}
                                className="rounded-full p-0.5 text-green-900 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-700"
                                aria-label={`Remove ${selectedHost.name} as host`}
                            >
                                <X className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                        </span>
                    ) : (
                        <span className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-red-900">
                            {isDenied ? "Deny-listed" : "No host"}
                        </span>
                    )}
                    {showCohosts &&
                        selectedCohosts.map((cohost) => (
                            <span
                                key={cohost.id}
                                className="inline-flex items-center gap-2 rounded-md border border-blue-300 bg-blue-50 px-3 py-1.5 font-dmSans text-sm font-semibold text-blue-900"
                            >
                                Co-host: {cohost.name}
                                <button
                                    type="button"
                                    onClick={() =>
                                        onToggleCohost(groupKey, cohost, true)
                                    }
                                    className="rounded-full p-0.5 text-blue-900 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-700"
                                    aria-label={`Remove ${cohost.name} as co-host`}
                                >
                                    <X
                                        className="h-3.5 w-3.5"
                                        aria-hidden="true"
                                    />
                                </button>
                            </span>
                        ))}
                </div>
            )}
            {options && (
                <section
                    aria-labelledby={`podcast-candidates-${groupKey}`}
                    className="grid gap-2 rounded-md border border-subtle bg-surface-elevated p-3"
                >
                    <h3
                        id={`podcast-candidates-${groupKey}`}
                        className="font-dmSans text-sm font-semibold text-foreground"
                    >
                        Candidates
                    </h3>
                    <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                        {options.map((option) => {
                            const isHost = selectedHost?.id === option.id;
                            const isCohost = selectedCohosts.some(
                                (cohost) => cohost.id === option.id,
                            );
                            return (
                                <div
                                    key={option.id}
                                    className={`grid gap-2 rounded-md border p-3 font-dmSans ${
                                        isHost
                                            ? "border-green-500 bg-green-50"
                                            : isCohost
                                              ? "border-blue-500 bg-blue-50"
                                              : "border-strong bg-surface-elevated"
                                    }`}
                                >
                                    <div className="grid gap-1">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="font-semibold text-foreground">
                                                {option.name}
                                            </span>
                                            {option.confidence !==
                                                undefined && (
                                                <span className="text-caption font-normal text-muted-foreground">
                                                    {formatPercent(
                                                        option.confidence,
                                                    )}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-caption font-semibold text-muted-foreground">
                                            {formatAssociationType(
                                                option.associationType,
                                            )}
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                onSelectHost(groupKey, option)
                                            }
                                            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm font-semibold ${
                                                isHost
                                                    ? "border-green-500 bg-green-600 text-white"
                                                    : "border-strong bg-surface-elevated text-foreground hover:border-copper"
                                            }`}
                                            aria-label={`Set ${option.name} as host`}
                                        >
                                            <Plus
                                                className="h-3.5 w-3.5"
                                                aria-hidden="true"
                                            />
                                            Host
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() =>
                                                onToggleCohost(
                                                    groupKey,
                                                    option,
                                                    isCohost,
                                                )
                                            }
                                            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm font-semibold ${
                                                isCohost
                                                    ? "border-blue-500 bg-blue-600 text-white"
                                                    : "border-strong bg-surface-elevated text-foreground hover:border-copper"
                                            }`}
                                            aria-label={`Set ${option.name} as co-host`}
                                        >
                                            <Plus
                                                className="h-3.5 w-3.5"
                                                aria-hidden="true"
                                            />
                                            Co-host
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}
        </>
    );
}
