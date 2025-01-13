/* eslint-disable @typescript-eslint/no-explicit-any */
import TableFilterBar from "@/ui/components/filter";
import ClubCarouselCard from "@/ui/components/cards/carousel/club";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";

export default async function ClubSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, filters } = await makeRequest<ClubSearchResponse>(
        APIRoutePath.ClubSearch,
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
                    data.entities.map((entity) => {
                        return (
                            <ClubCarouselCard
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
