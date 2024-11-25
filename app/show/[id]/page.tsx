/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../components/container";
import { EntityType } from "../../../objects/enum";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { getDB } from "../../../database";
const { database } = getDB();
import ScrapeEntityModal from "../../../components/modals/scrape";
import ModifyLineupModal from "../../../components/modals/modifyLineup";
import TagEntityModal from "../../../components/modals/tagEntity";
import EntityBanner from "../../../components/banner";

export default async function ShowDetailPage(props: any) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        props.params,
    );
    const { entity, total } = await database.page.getShowDetailPageData(
        helper.asQueryFilters(),
    );

    const entityString = JSON.stringify(entity);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);
    return (
        <main className="flex-grow pt-5 bg-shark">
            <section>
                <ScrapeEntityModal
                    entityId={entity.id}
                    type={EntityType.Show}
                />
                <ModifyLineupModal entityString={entityString} />
                <TagEntityModal
                    type={EntityType.Show}
                    entityId={entity.id}
                    tagsString={entityString}
                />
            </section>
            <section>
                <EntityBanner entityString={entityString} />
            </section>
            <section>
                <QueryableEntityTableContainer
                    entityType={EntityType.Comedian}
                    totalEntities={total}
                    entityCollectionString={containedEntitiesString}
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
