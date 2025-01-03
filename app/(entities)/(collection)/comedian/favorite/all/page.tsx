import TableFilterBar from "../../../../../../components/filter";

export default async function FavoriteComediansPage() {
    // const filters = await QueryHelper.storePageParams(
    //     props.searchParams,
    //     props.params,
    // );

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section>
                <TableFilterBar totalItems={0} filtersString="" />
            </section>
            <section className="grid grid-cols-1 gap-y-10">
                {/* {data.entities.length > 0 ? (
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
                )} */}
            </section>
        </main>
    );
}
