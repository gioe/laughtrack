import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import DetailTabs, { DetailTab } from "@/ui/pages/entity/detailTabs";
import ShowLineupSection from "@/ui/pages/entity/show/lineupSection";
import RelatedShowsSection from "@/ui/pages/entity/show/relatedShows";

interface ShowDetailTabsProps {
    clubName?: string;
    lineup: ComedianLineupDTO[];
    relatedShows: ShowDTO[];
}

export default function ShowDetailTabs({
    clubName,
    lineup,
    relatedShows,
}: ShowDetailTabsProps) {
    const hasLineup = lineup.length > 0;
    const hasRelatedShows = relatedShows.length > 0;

    if (hasLineup && hasRelatedShows) {
        return (
            <DetailTabs
                ariaLabel="Show detail sections"
                className="mt-8"
                defaultTabId="lineup"
                tabIdPrefix="show-detail"
            >
                <DetailTab id="lineup" label="Lineup">
                    <ShowLineupSection lineup={lineup} />
                </DetailTab>
                <DetailTab id="more-shows" label="More shows">
                    <RelatedShowsSection
                        shows={relatedShows}
                        clubName={clubName}
                    />
                </DetailTab>
            </DetailTabs>
        );
    }

    return (
        <>
            {hasLineup ? <ShowLineupSection lineup={lineup} /> : null}
            <RelatedShowsSection shows={relatedShows} clubName={clubName} />
        </>
    );
}
