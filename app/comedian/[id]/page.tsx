import EntityBanner from "../../../components/banner";
import TagEntityModal from "../../../components/modals/tag";
import QueryableEntityTableContainer from "../../../components/container";
import MergeComediansModal from "../../../components/modals/merge";
import EditSocialDataModal from "../../../components/modals/editSocialData";
import { getDB } from "../../../database";
import { SearchParams } from "../../../objects/type/searchParams";
import { PaginatedEntityResponse } from "../../../objects/interface";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
const { db } = getDB();

async function getComedianDetail(
    slug: string,
    searchParams: SearchParams,
): Promise<PaginatedEntityResponse> {
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    return db.comedians.getByName(slug, paramsWrapper);
}

export default async function ComedianDetailsPage(props: {
    params: Promise<{ slug: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const response = await getComedianDetail(params.slug, searchParams);
    const entityString = JSON.stringify(response.entity);
    const entityCollectionString = JSON.stringify(
        response.entity.containedEntities,
    );
    return (
        <main className="flex-grow pt-5 bg-shark">
            <MergeComediansModal entityString={entityString} />
            <EditSocialDataModal entityString={entityString} />
            <TagEntityModal
                type={EntityType.Comedian}
                entityId={response.entity.id}
                tagsString={""}
            />
            <section>
                <EntityBanner entityString={entityString} />
            </section>
            <section>
                <section>
                    <QueryableEntityTableContainer
                        entityType={EntityType.Show}
                        totalEntities={response.total}
                        entityCollectionString={entityCollectionString}
                        defaultNode={
                            <h2 className="font-bold text-5xl text-white pt-6">
                                No upcoming shows for this club
                            </h2>
                        }
                    />
                </section>
            </section>
        </main>
    );
}
