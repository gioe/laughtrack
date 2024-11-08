import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import FilterPageContainer from "../../..//components/custom/filters/FilterPageContainer";
import ClearShowsModal from "../../..//components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "../../..//components/custom/modals/ScrapeClubModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { Club } from "../../../objects/classes/club/Club";
const { db } = getDB();

interface ClubDetailPageInterface {
    club: Club | null;
    tags: TagInterface[];
}

async function getClubDetail(id: string): Promise<ClubDetailPageInterface> {
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
    const { tags, club } = await getClubDetail(params.id);

    return (
        <div>
            {club && (
                <main className="flex-grow pt-5 bg-shark">
                    <ScrapeClubModal club={club} />
                    <ClearShowsModal club={club} />
                    <TagEntityModal entity={club} tags={tags} />
                    <section>
                        <EntityBanner entity={club} />
                    </section>
                    <section>
                        <FilterPageContainer
                            resultString={JSON.stringify(club.dates)}
                            defaultNode={<div></div>}
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
