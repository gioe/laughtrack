import ShowTable from "../../components/custom/tables/ShowTable";
import FilterPageContainer from "../../components/custom/filters/FilterPageContainer";
import { SORT_OPTIONS } from "../../util/sort";
import { Suspense } from "react";
import { SearchParams } from "../../interfaces/searchParams.interface";

export default async function SearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer
                itemCount={2}
                sortOptions={SORT_OPTIONS.SHOW}
                child={
                    <Suspense
                        key={
                            (searchParams?.query ?? 1) +
                            (searchParams?.page ?? "")
                        }
                        fallback={<div />}
                    >
                        <ShowTable params={searchParams} />
                    </Suspense>
                }
            />
        </main>
    );
}
