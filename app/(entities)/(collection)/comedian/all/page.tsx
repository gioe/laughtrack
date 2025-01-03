/* eslint-disable @typescript-eslint/no-explicit-any */
import ComedianCarouselCard from "../../../../../components/cards/carousel/comedian";
import TableFilterBar from "../../../../../components/filter";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../objects/enum";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { GetTagsResponse } from "../../../../api/tag/route";
import { ComedianSearchResponse } from "./interface";

export default async function ComedianSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        RoutePath.ComedianSearch,
        paramsWrapper.asUrlSearchParams(),
        CACHE.search,
    )) as ComedianSearchResponse;

    const filterResponse = await executeGet<GetTagsResponse>(`/api/tag`).then(
        (response) => {
            if (response) {
                return response.containers;
            }
        },
    );

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar
                    totalItems={data.total}
                    filtersString={JSON.stringify(filterResponse)}
                />
            </section>
            <section className="grid grid-cols-1 gap-y-10">
                {data.entities.length > 0 ? (
                    data.entities.map((entity) => {
                        return (
                            <ComedianCarouselCard
                                key={entity.name}
                                entity={JSON.stringify(entity)}
                            />
                        );
                    })
                ) : (
                    <div className="max-w-7xl">
                        <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                            No comedians found. Who knows why.
                        </h2>
                    </div>
                )}
            </section>
        </main>
    );
}
