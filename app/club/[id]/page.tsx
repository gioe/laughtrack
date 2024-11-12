import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/banner";
import { getSortOptionsForEntityType } from "../../../util/sort";
import QueryableEntityTableContainer from "../../../components/container";
import ClearShowsModal from "../../../components/modals/club/clear";
import ScrapeEntityModal from "../../../components/modals/entity/scrape";
import { SearchParams } from "../../../objects/types/searchParams";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";
import { PaginatedEntityResponse } from "../../../objects/interfaces/entity.interface";
const { db } = getDB();

async function getClubDetail(
    id: string,
    searchParams: SearchParams,
): Promise<PaginatedEntityResponse> {
    const paramsWrapper =
        LaughtrackSearchParams.asServerSideParams(searchParams);
    return db.clubs.getById(Number(id), paramsWrapper);
}

export default async function ClubDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const response = await getClubDetail(params.id, searchParams);
    const responseString = JSON.stringify(response.entity);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <ScrapeEntityModal
                entityId={response.entity.id}
                type={EntityType.Club}
            />
            <ClearShowsModal clubId={response.entity.id} />
            <section>
                <EntityBanner entityString={responseString} />
            </section>
            <section>
                <QueryableEntityTableContainer
                    sortOptions={getSortOptionsForEntityType(EntityType.Show)}
                    responseString={responseString}
                    defaultNode={
                        <h2 className="font-bold text-5xl text-white pt-6">
                            No shows for this club
                        </h2>
                    }
                />
            </section>
        </main>
    );
}
