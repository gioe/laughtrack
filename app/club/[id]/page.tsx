import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/custom/banner";
import FilterPageContainer from "../../..//components/custom/filters/FilterPageContainer";
import ClearShowsModal from "../../..//components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "../../..//components/custom/modals/ScrapeClubModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { Club } from "../../../objects/classes/club/Club";
import { getSortOptionsForEntityType } from "../../../util/sort";
const { db } = getDB();

interface ClubDetailPageInterface {
    club: Club | null;
    tags: TagInterface[];
}

async function getClubDetail(
    id: string,
    searchParams: SearchParams,
): Promise<ClubDetailPageInterface> {
    const club = db.clubs.getByName(id);
    const tags = db.tags.getByType(EntityType.Club.valueOf());

    return Promise.all([club, tags]).then((responses) => {
        const club = responses[0];
        const tags = responses[1];
        return {
            club,
            tags,
        };
    });
}

export default async function ClubDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const { tags, club } = await getClubDetail(params.id, searchParams);
    const clubString = JSON.stringify(club);
    const tagsString = JSON.stringify(tags);
    const sortOptions = getSortOptionsForEntityType(EntityType.Show);

    return (
        <div>
            {club && (
                <main className="flex-grow pt-5 bg-shark">
                    <ScrapeClubModal clubString={clubString} />
                    <ClearShowsModal clubString={clubString} />
                    <TagEntityModal
                        entityString={clubString}
                        tagsString={tagsString}
                    />
                    <section>
                        <EntityBanner entityString={clubString} />
                    </section>
                    <section>
                        <FilterPageContainer
                            sortOptions={sortOptions}
                            resultString={JSON.stringify(club.dates)}
                            defaultNode={<div></div>}
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
