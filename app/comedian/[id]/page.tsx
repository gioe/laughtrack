import QueryableEntityTableContainer from "../../../components/container";
import { URLParams } from "../../../objects/type/urlParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
import { headers } from "next/headers";
import { HeadersWrapper } from "../../../objects/class/headers/HeadersWrapper";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { SlugInterface } from "../../../objects/interface";
import { ComedianDetailDTO, ComedianDetailPageData } from "./interface";
import { comedianDetailPageMapper as mapper } from "./mapper";
import { SlugWrapper } from "../../../objects/class/slug/SlugWrapper";

export default async function ComedianDetailsPage(props: {
    params: Promise<SlugInterface>;
    searchParams: Promise<URLParams>;
}) {
    await SlugWrapper.updateSlug(props.params);
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);

    const { entity, total } = await QueryHelper.getPageData<
        ComedianDetailDTO,
        ComedianDetailPageData
    >(mapper);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <section>
                <section>
                    <QueryableEntityTableContainer
                        entityType={EntityType.Show}
                        totalEntities={total}
                        entityCollectionString={containedEntitiesString}
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
