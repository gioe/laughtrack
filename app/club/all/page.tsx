import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { getDB } from "../../../database";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { Club } from "../../../objects/classes/club/Club";
import BasicEntityCard from "../../../components/custom/tables/cards/BasicEntityCard";

const { db } = getDB();

export default async function AllClubsPage(props: {
    searchParams?: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const clubs = await db.clubs.getAll();

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer<Club>
                suspenseKey={
                    (searchParams?.query ?? "") + (searchParams?.page ?? 0)
                }
                renderItem={(entity) => {
                    return <BasicEntityCard entity={entity} />;
                }}
                results={clubs}
                defaultNode={<div></div>}
            />
        </main>
    );
}
