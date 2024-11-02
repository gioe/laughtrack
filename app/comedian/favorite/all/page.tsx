import ComedianTable from "../../../../components/custom/tables/ComedianTable";
import { Suspense } from "react";
import { SearchParams } from "../../../../interfaces/searchParams.interface";

export default async function FavoriteComediansPage(props: {
    searchParams?: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;

    return (
        <main className="flex-grow pt-5 bg-shark">
            <Suspense
                key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")}
                fallback={<div />}
            >
                <ComedianTable params={searchParams} />
            </Suspense>
        </main>
    );
}
