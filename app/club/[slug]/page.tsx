import { EntityType } from "../../../objects/enum";
import QueryableEntityTableContainer from "../../../components/container";
import { URLParams } from "../../../objects/type/urlParams";
import { SlugInterface } from "../../../objects/interface";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { headers } from "next/headers";
import ScrapeEntityModal from "../../../components/modals/scrape";
import ClearShowsModal from "../../../components/modals/clearClub";
import EntityBanner from "../../../components/banner";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ClubDetailPage(props: {
    params: Promise<SlugInterface>;
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storePageParams(
        props.searchParams,
        headers(),
        props.params,
    );

    const { entity, total } = await database.page.getClubDetailPageData();

    const containedEntitiesString = JSON.stringify(entity.containedEntities);
    const entityString = JSON.stringify(entity);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <section>
                <ScrapeEntityModal
                    entityId={entity.id}
                    type={EntityType.Club}
                />
                <ClearShowsModal clubId={entity.id} />
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
                            No shows for this club
                        </h2>
                    }
                />
            </section>
        </main>
    );
}
