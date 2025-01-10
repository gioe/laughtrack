/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "../../../../../objects/enum";
import { ShowSearchResponse } from "./interface";
import TableFilterBar from "../../../../../components/filter";
import ShowCard from "../../../../../components/cards/show";
import { Show } from "../../../../../objects/class/show/Show";
import { makeRequest } from "../../../../../util/actions/makeRequest";

export default async function ShowSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, filters } = await makeRequest<ShowSearchResponse>(
        APIRoutePath.ShowSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
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
