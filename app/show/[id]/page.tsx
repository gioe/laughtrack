import QueryableEntityTableContainer from "../../../components/container";
import ModifyLineupModal from "../../../components/modals/modifyLineup";
import ScrapeEntityModal from "../../../components/modals/scrape";
import EntityBanner from "../../../components/banner";
import TagEntityModal from "../../../components/modals/tag";
import { getDB } from "../../../database";
import { EntityType } from "../../../objects/enum";
import { SearchParams } from "../../../objects/type/searchParams";
import { PaginatedEntityResponse } from "../../../objects/interface";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
const { db } = getDB();

async function getShowDetail(
    slug: string,
    searchParams: SearchParams,
): Promise<PaginatedEntityResponse> {
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    return db.shows.getById(Number(slug), paramsWrapper);
}

export default async function ShowDetailPage(props: {
    params: Promise<{ slug: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const response = await getShowDetail(params.slug, searchParams);
    const entityString = JSON.stringify(response.entity);
    const entityCollectionString = JSON.stringify(
        response.entity.containedEntities,
    );

    return (
        <main className="flex-grow pt-5 bg-shark">
            <ScrapeEntityModal
                entityId={response.entity.id}
                type={EntityType.Show}
            />
            <ModifyLineupModal entityString={entityString} />
            <TagEntityModal
                type={EntityType.Show}
                entityId={response.entity.id}
                tagsString={""}
            />
            <section>
                <EntityBanner entityString={entityString} />
            </section>
            <section>
                <QueryableEntityTableContainer
                    entityType={EntityType.Comedian}
                    totalEntities={response.total}
                    entityCollectionString={entityCollectionString}
                    defaultNode={
                        <h2 className="font-bold text-5xl text-white pt-6">
                            No comedians on this show
                        </h2>
                    }
                />
            </section>
        </main>
    );
}
