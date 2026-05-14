import React from "react";
import { ExternalLink } from "lucide-react";
import { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";

interface PodcastAppearancesSectionProps {
    appearances: ComedianPodcastAppearanceDTO[];
}

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
});

function formatReleaseDate(date: Date | string | null): string {
    if (!date) return "Release date unavailable";

    return DATE_FORMATTER.format(date instanceof Date ? date : new Date(date));
}

const PodcastAppearancesSection = ({
    appearances,
}: PodcastAppearancesSectionProps) => {
    if (appearances.length === 0) return null;

    return (
        <section
            aria-labelledby="recent-podcast-appearances-heading"
            className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-8 pb-2"
        >
            <header className="mb-4">
                <h2
                    id="recent-podcast-appearances-heading"
                    className="font-gilroy-bold text-h2 font-bold text-foreground"
                >
                    Recent podcast appearances
                </h2>
            </header>

            <ul
                role="list"
                className="divide-y divide-gray-200 border-y border-gray-200"
            >
                {appearances.map((appearance) => (
                    <li key={appearance.id}>
                        <a
                            href={appearance.episodeUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex items-start justify-between gap-4 py-4 transition-colors hover:bg-coconut-cream/40"
                        >
                            <span className="min-w-0">
                                <span className="block font-gilroy-bold text-base font-bold text-foreground group-hover:text-copper">
                                    {appearance.episodeTitle}
                                </span>
                                <span className="mt-1 block font-dmSans text-sm text-gray-600">
                                    {appearance.podcastName} ·{" "}
                                    {formatReleaseDate(appearance.releaseDate)}
                                </span>
                            </span>
                            <ExternalLink
                                size={18}
                                className="mt-1 flex-shrink-0 text-gray-400 group-hover:text-copper"
                                aria-hidden="true"
                            />
                        </a>
                    </li>
                ))}
            </ul>
        </section>
    );
};

export default PodcastAppearancesSection;
