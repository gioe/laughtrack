import ClubTable from "../../../components/custom/tables/ClubTable";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { db } from "../../../database";
import { SORT_OPTIONS } from "../../../util/sort";
import { Suspense } from "react";
import { SearchParams } from "../../../interfaces/searchParams.interface";

export default async function AllClubsPage(props: {
    searchParams?: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const clubs = await db.clubs.getAll(searchParams);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer
                itemCount={10}
                sortOptions={SORT_OPTIONS.CLUB}
                child={
                    <Suspense
                        key={
                            (searchParams?.query ?? 1) +
                            (searchParams?.page ?? "")
                        }
                        fallback={<div />}
                    >
                        <ClubTable clubs={clubs} />
                    </Suspense>
                }
            />
        </main>
    );
}
