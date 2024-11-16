import QueryableEntityTableContainer from "../../../components/container";
import { EntityType } from "../../../objects/enum";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { headers } from "next/headers";
import { HeadersWrapper } from "../../../objects/class/headers/HeadersWrapper";
import { URLParams } from "../../../objects/type/urlParams";
import { ShowDetailDTO, ShowDetailPageData } from "./interface";
import { showDetailPageMapper as mapper } from "./mapper";
import { SlugWrapper } from "../../../objects/class/slug/SlugWrapper";

export default async function ShowDetailPage(props: {
    params: Promise<{ slug: string }>;
    searchParams: Promise<URLParams>;
}) {
    await SlugWrapper.updateSlug(props.params);
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);

    const { entity, total } = await QueryHelper.getPageData<
        ShowDetailDTO,
        ShowDetailPageData
    >(mapper);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);

    return (
        <main className="flex-grow pt-5 bg-shark">
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
