"use client";

import { useState } from "react";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { FilterDTO } from "@/objects/interface";
import { SearchVariant } from "@/objects/enum/searchVariant";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import PastShowsSection from "@/ui/pages/entity/comedian/pastShows";
import RelatedComediansSection from "@/ui/pages/entity/comedian/related";
import PodcastAppearancesSection from "@/ui/pages/entity/comedian/podcastAppearances";

type ComedianDetailTab = "shows" | "podcasts";

interface ComedianDetailTabsProps {
    shows: ShowDTO[];
    total: number;
    filters: FilterDTO[];
    comedianName: string;
    relatedComedians: ComedianDTO[];
    podcastAppearances: ComedianPodcastAppearanceDTO[];
}

const tabs: Array<{ id: ComedianDetailTab; label: string }> = [
    { id: "shows", label: "Shows" },
    { id: "podcasts", label: "Podcasts" },
];

const panelClasses = "max-w-7xl mx-auto pt-6";

const ComedianDetailTabs = ({
    shows,
    total,
    filters,
    comedianName,
    relatedComedians,
    podcastAppearances,
}: ComedianDetailTabsProps) => {
    const [activeTab, setActiveTab] = useState<ComedianDetailTab>("shows");
    const [activatedTabs, setActivatedTabs] = useState<
        Record<ComedianDetailTab, boolean>
    >({
        shows: true,
        podcasts: false,
    });

    const activateTab = (tab: ComedianDetailTab) => {
        setActiveTab(tab);
        setActivatedTabs((prev) => ({ ...prev, [tab]: true }));
    };

    return (
        <section className="mt-2">
            <div className="sticky top-0 z-20 border-y border-gray-200 bg-white/95 backdrop-blur">
                <div
                    role="tablist"
                    aria-label="Comedian detail sections"
                    className="max-w-7xl mx-auto flex overflow-x-auto px-4 sm:px-6 md:px-8"
                >
                    {tabs.map((tab) => {
                        const selected = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                id={`comedian-detail-tab-${tab.id}`}
                                type="button"
                                role="tab"
                                aria-selected={selected}
                                aria-controls={`comedian-detail-panel-${tab.id}`}
                                onClick={() => activateTab(tab.id)}
                                className={`whitespace-nowrap border-b-2 px-4 py-3 font-dmSans text-sm font-medium transition-colors ${
                                    selected
                                        ? "border-copper text-copper"
                                        : "border-transparent text-gray-600 hover:border-gray-300 hover:text-foreground"
                                }`}
                            >
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div
                id="comedian-detail-panel-shows"
                role="tabpanel"
                aria-labelledby="comedian-detail-tab-shows"
                hidden={activeTab !== "shows"}
                className={panelClasses}
            >
                <div id="comedian-upcoming-shows">
                    <FilterBar
                        variant={SearchVariant.ComedianDetail}
                        total={total}
                        filterData={filters}
                    />
                    <ShowTable shows={shows} cardContext="comedian-detail" />
                </div>

                <div className="mt-10">
                    <PastShowsSection
                        comedianName={comedianName}
                        showCardContext="comedian-detail"
                    />
                </div>

                <div className="mt-10">
                    <RelatedComediansSection
                        comedians={relatedComedians}
                        subjectName={comedianName}
                    />
                </div>
            </div>

            {activatedTabs.podcasts && (
                <div
                    id="comedian-detail-panel-podcasts"
                    role="tabpanel"
                    aria-labelledby="comedian-detail-tab-podcasts"
                    hidden={activeTab !== "podcasts"}
                    className={panelClasses}
                >
                    <PodcastAppearancesSection
                        appearances={podcastAppearances}
                    />
                </div>
            )}
        </section>
    );
};

export default ComedianDetailTabs;
