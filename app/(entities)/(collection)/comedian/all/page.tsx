/* eslint-disable @typescript-eslint/no-explicit-any */
import TableFilterBar from "@/ui/components/filter";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import ComedianCarouselCard from "@/ui/components/cards/carousel/comedian";
import { Key } from "react";

export default async function ComedianSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, filters } = await makeRequest<ComedianSearchResponse>(
        APIRoutePath.ComedianSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.search,
        },
    );

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar
                    totalItems={data.total}
                    filtersString={JSON.stringify(filters)}
                />
            </section>
            <section className="grid grid-cols-1 gap-y-10">
                {data.entities.length > 0 ? (
                    data.entities.map(
                        (entity: { name: Key | null | undefined }) => {
                            return (
                                <ComedianCarouselCard
                                    key={entity.name}
                                    entity={JSON.stringify(entity)}
                                />
                            );
                        },
                    )
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
