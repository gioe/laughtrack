import { Suspense } from "react";
import ComedianTable from "../../../components/custom/tables/ComedianTable";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { SORT_OPTIONS } from "../../../util/sort";
import { SearchParams } from "../../../interfaces/searchParams.interface";

export default async function AllComediansPage(props: {
    searchParams?: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer
                itemCount={10}
                sortOptions={SORT_OPTIONS.COMEDIAN}
                child={
                    <Suspense
                        key={
                            (searchParams?.query ?? 1) +
                            (searchParams?.page ?? "")
                        }
                        fallback={<div />}
                    >
                        <ComedianTable params={searchParams} />
                    </Suspense>
                }
            />
        </main>
    );
}
