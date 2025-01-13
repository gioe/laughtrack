import TableFilterBar from "@/ui/components/filter";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ClubDetailPageResponse } from "@/app/api/club/[name]/interface";
import ShowCard from "@/ui/components/cards/show";
import { Show } from "@/objects/class/show/Show";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data, filters } = await makeRequest<ClubDetailPageResponse>(
        APIRoutePath.Club + `/${paramsWrapper.asSlug()}`,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.detailPage,
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
                {data.entity.containedEntities.length > 0 ? (
                    data.entity.containedEntities.map((entity) => {
                        return (
                            <ShowCard
                                key={`${entity.name}-${entity.id}`}
                                show={entity as Show}
                            />
                        );
                    })
                ) : (
                    <div className="max-w-7xl">
                        <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                            No shows for this club
                        </h2>
                    </div>
                )}
            </section>
        </main>
    );
}
