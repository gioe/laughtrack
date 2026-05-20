import type { SiblingClubDTO } from "@/lib/data/club/detail/findSiblingClubs";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { FilterDTO } from "@/objects/interface";
import { SearchVariant } from "@/objects/enum/searchVariant";
import DetailTabs, { DetailTab } from "@/ui/pages/entity/detailTabs";
import ClubShowRooms from "@/ui/pages/entity/club/showRooms";
import SiblingLocations from "@/ui/pages/entity/club/siblings";
import FilterBar from "@/ui/pages/search/filterBar";

interface ClubDetailTabsProps {
    chainName: string | null;
    filters: FilterDTO[];
    shows: ShowDTO[];
    siblings: SiblingClubDTO[];
    total: number;
}

export default function ClubDetailTabs({
    chainName,
    filters,
    shows,
    siblings,
    total,
}: ClubDetailTabsProps) {
    const chainLabel = chainName;
    const showsPanel = (
        <>
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filterData={filters}
            />
            <ClubShowRooms shows={shows} />
        </>
    );

    if (!chainLabel || siblings.length === 0) {
        return showsPanel;
    }

    return (
        <DetailTabs
            ariaLabel="Club detail sections"
            defaultTabId="shows"
            panelClassName="pt-6"
            tabIdPrefix="club-detail"
        >
            <DetailTab id="shows" label="Shows">
                {showsPanel}
            </DetailTab>
            <DetailTab id="locations" label="Locations">
                <SiblingLocations chainName={chainLabel} siblings={siblings} />
            </DetailTab>
        </DetailTabs>
    );
}
