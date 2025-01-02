/* eslint-disable @typescript-eslint/no-explicit-any */
import ClubCarouselCard from "../../../../../components/cards/carousel/club";
import TableFilterBar from "../../../../../components/filter";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../objects/enum";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { ClubSearchResponse } from "./interface";

export default async function ClubSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        RoutePath.ClubSearch,
        paramsWrapper.asUrlSearchParams(),
        CACHE.search,
    )) as ClubSearchResponse;

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar totalItems={data.entities.length} />
            </section>
            <section className="grid grid-cols-1 gap-y-10">
                {data.entities.length > 0 ? (
                    data.entities.map((entity) => {
                        return (
                            <ClubCarouselCard
                                key={entity.name}
                                club={{
                                    name: entity.name,
                                    count: 0,
                                }}
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
