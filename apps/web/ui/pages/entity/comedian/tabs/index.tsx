import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { FilterDTO } from "@/objects/interface";
import { SearchVariant } from "@/objects/enum/searchVariant";
import DetailTabs, { DetailTab } from "@/ui/pages/entity/detailTabs";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import PastShowsSection from "@/ui/pages/entity/comedian/pastShows";
import RelatedComediansSection from "@/ui/pages/entity/comedian/related";
import PodcastAppearancesSection from "@/ui/pages/entity/comedian/podcastAppearances";

interface ComedianDetailTabsProps {
    shows: ShowDTO[];
    total: number;
    filters: FilterDTO[];
    comedianName: string;
    relatedComedians: ComedianDTO[];
    podcastAppearances: ComedianPodcastAppearanceDTO[];
}

const panelClasses = "max-w-7xl mx-auto pt-6";

const ComedianDetailTabs = ({
    shows,
    total,
    filters,
    comedianName,
    relatedComedians,
    podcastAppearances,
}: ComedianDetailTabsProps) => {
    return (
        <DetailTabs
            ariaLabel="Comedian detail sections"
            defaultTabId="shows"
            panelClassName={panelClasses}
            tabIdPrefix="comedian-detail"
        >
            <DetailTab id="shows" label="Shows">
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
            </DetailTab>
            <DetailTab id="podcasts" label="Podcasts" lazy>
                <PodcastAppearancesSection appearances={podcastAppearances} />
            </DetailTab>
        </DetailTabs>
    );
};

export default ComedianDetailTabs;
