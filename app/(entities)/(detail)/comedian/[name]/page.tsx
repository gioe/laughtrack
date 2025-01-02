/* eslint-disable @typescript-eslint/no-explicit-any */
import ShowCard from "../../../../../components/cards/show";
import TableFilterBar from "../../../../../components/filter";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { Show } from "../../../../../objects/class/show/Show";
import { RoutePath } from "../../../../../objects/enum";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { ComedianDetailPageResponse } from "./interface";

export default async function ComedianDetailsPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ComedianDetail + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
        CACHE.detailPage,
    )) as ComedianDetailPageResponse;

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar totalItems={data.total} />
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
                            No upcoming shows for this comedian
                        </h2>
                    </div>
                )}
            </section>
        </main>
    );
}
