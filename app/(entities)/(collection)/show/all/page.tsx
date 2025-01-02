/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { EntityType, RoutePath } from "../../../../../objects/enum";
import { executeGet } from "../../../../../util/actions/executeGet";
import { ShowSearchResponse } from "./interface";
import TableFilterBar from "../../../../../components/filter";
import ShowCard from "../../../../../components/cards/show";
import { Show } from "../../../../../objects/class/show/Show";
import { Filter } from "../../../../../objects/class/tag/Filter";
import { TagDataDTO } from "../../../../../objects/interface/tag.interface";

export default async function ShowSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        RoutePath.ShowSearch,
        paramsWrapper.asUrlSearchParams(),
    )) as ShowSearchResponse;
    const filterResponse = await executeGet<any>(`/api/tag`).then(
        (response) => {
            if (data) {
                console.log(response);
                return response.containers
                    .map((dto: TagDataDTO) => {
                        return new Filter(dto, null);
                    })
                    .filter((filter: Filter) => filter.type == EntityType.Show);
            }
        },
    );

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar
                    totalItems={data.entities.length}
                    filtersString={JSON.stringify(filterResponse)}
                />
            </section>
            <section className="grid grid-cols-1 gap-y-10">
                {data.entities.length > 0 ? (
                    data.entities.map((entity) => {
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
                            No upcoming shows. Check back later.
                        </h2>
                    </div>
                )}
            </section>
        </main>
    );
}
