import { executeGet } from "../../../../../util/actions/executeGet";
import { ClubDetailPageResponse } from "./interface";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { RoutePath } from "../../../../../objects/enum";
import ShowCard from "../../../../../components/cards/show";
import { Show } from "../../../../../objects/class/show/Show";
import TableFilterBar from "../../../../../components/filter";

export default async function ClubDetailPage(props) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ClubDetail + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
        CACHE.detailPage,
    )) as ClubDetailPageResponse;

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
                            No shows for this club
                        </h2>
                    </div>
                )}
            </section>
        </main>
    );
}
