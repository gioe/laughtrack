import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/banner";
import { Club } from "../../../objects/classes/club/Club";
import { getSortOptionsForEntityType } from "../../../util/sort";
import QueryableTableContainer from "../../../components/container";
import ClearShowsModal from "../../../components/modals/club/clear";
import ScrapeEntityModal from "../../../components/modals/club/scrape";
const { db } = getDB();

async function getClubDetail(
    id: string,
    searchParams: SearchParams,
): Promise<Club | null> {
    return db.clubs.getById(Number(id), searchParams);
}

export default async function ClubDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const club = await getClubDetail(params.id, searchParams);
    const clubString = JSON.stringify(club);
    const sortOptions = getSortOptionsForEntityType(EntityType.Show);

    return (
        <div>
            {club && (
                <main className="flex-grow pt-5 bg-shark">
                    <ScrapeEntityModal
                        entityId={club.id}
                        type={EntityType.Club}
                    />
                    <ClearShowsModal clubId={club.id} />
                    <section>
                        <EntityBanner entityString={clubString} />
                    </section>
                    <section>
                        <QueryableTableContainer
                            sortOptions={sortOptions}
                            resultString={JSON.stringify(club.dates)}
                            defaultNode={
                                <h2 className="font-bold text-5xl text-white pt-6">
                                    No shows for this club
                                </h2>
                            }
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
