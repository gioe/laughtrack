import { EntityType } from "../../../objects/enum";
import QueryableEntityTableContainer from "../../../components/container";
import { URLParams } from "../../../objects/type/urlParams";
import { SlugInterface } from "../../../objects/interface";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { HeadersWrapper } from "../../../objects/class/headers/HeadersWrapper";
import { headers } from "next/headers";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { ClubDetailDTO, ClubDetailPageData } from "./interface";
import { clubDetailPageMapper as mapper } from "./mapper";
import { SlugWrapper } from "../../../objects/class/slug/SlugWrapper";

export default async function ClubDetailPage(props: {
    params: Promise<SlugInterface>;
    searchParams: Promise<URLParams>;
}) {
    await SlugWrapper.updateSlug(props.params);
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);

    const { entity, total } = await QueryHelper.getPageData<
        ClubDetailDTO,
        ClubDetailPageData
    >(mapper);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);

    return (
        <main className="flex-grow pt-5 bg-shark">
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
