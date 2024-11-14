import { EntityType } from "../../../objects/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/banner";
import QueryableEntityTableContainer from "../../../components/container";
import ClearShowsModal from "../../../components/modals/clear";
import ScrapeEntityModal from "../../../components/modals/scrape";
import { SearchParams } from "../../../objects/type/searchParams";
import { PaginatedEntityResponse } from "../../../objects/interface";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
const { db } = getDB();

async function getClubDetail(
    slug: string,
    searchParams: SearchParams,
): Promise<PaginatedEntityResponse> {
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    return db.clubs.getByName(slug, paramsWrapper);
}

export default async function ClubDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const response = await getClubDetail(params.id, searchParams);

    const entityString = JSON.stringify(response.entity);
    const entityCollectionString = JSON.stringify(
        response.entity.containedEntities,
    );

    return (
        <main className="flex-grow pt-5 bg-shark">
            <ScrapeEntityModal
                entityId={response.entity.id}
                type={EntityType.Club}
            />
            <ClearShowsModal clubId={response.entity.id} />
            <section>
                <EntityBanner entityString={entityString} />
            </section>
            <section>
                <QueryableEntityTableContainer
                    entityType={EntityType.Show}
                    totalEntities={response.total}
                    entityCollectionString={entityCollectionString}
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
