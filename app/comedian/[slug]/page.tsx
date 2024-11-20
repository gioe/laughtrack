import QueryableEntityTableContainer from "../../../components/container";
import { URLParams } from "../../../objects/type/urlParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
import { headers } from "next/headers";
import { SlugInterface } from "../../../objects/interface";
import MergeComediansModal from "../../../components/modals/mergeComedians";
import EditSocialDataModal from "../../../components/modals/socialData";
import TagEntityModal from "../../../components/modals/tagEntity";
import EntityBanner from "../../../components/banner";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ComedianDetailsPage(props: {
    params: Promise<SlugInterface>;
    searchParams: Promise<URLParams>;
}) {
    const filters = await QueryHelper.storePageParams(
        props.searchParams,
        headers(),
        props.params,
    );

    const { entity, total } =
        await database.page.getComedianDetailPageData(filters);

    const entityString = JSON.stringify(entity);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);
    return (
        <main className="flex-grow pt-5 bg-shark">
            <section>
                <MergeComediansModal entityString={entityString} />
                <EditSocialDataModal entityString={entityString} />
                <TagEntityModal
                    type={EntityType.Comedian}
                    entityId={entity.id}
                    tagsString={""}
                />
            </section>
            <section>
                <EntityBanner entityString={entityString} />
            </section>
            <section>
                <QueryableEntityTableContainer
                    entityType={EntityType.Show}
                    totalEntities={total}
                    entityCollectionString={containedEntitiesString}
                    defaultNode={
                        <h2 className="font-bold text-5xl text-white pt-6">
                            No upcoming shows for this comedian
                        </h2>
                    }
                />
            </section>
        </main>
    );
}
