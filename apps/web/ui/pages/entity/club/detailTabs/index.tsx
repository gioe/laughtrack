import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { FilterDTO } from "@/objects/interface";
import { SearchVariant } from "@/objects/enum/searchVariant";
import SectionHeader from "@/ui/components/sectionHeader";
import ClubShowRooms from "@/ui/pages/entity/club/showRooms";
import FilterBar from "@/ui/pages/search/filterBar";

interface ClubDetailTabsProps {
    filters: FilterDTO[];
    shows: ShowDTO[];
    total: number;
    emptyShowsMessage?: string;
}

// Other locations in the club's chain are now surfaced via the location
// dropdown in the header (see ClubDetailHeader), so this just renders the
// club's own shows.
export default function ClubDetailTabs({
    filters,
    shows,
    total,
    emptyShowsMessage,
}: ClubDetailTabsProps) {
    return (
        <>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10">
                <SectionHeader eyebrow="Calendar" title="Search shows" />
            </div>
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filterData={filters}
            />
            <ClubShowRooms shows={shows} emptyMessage={emptyShowsMessage} />
        </>
    );
}
