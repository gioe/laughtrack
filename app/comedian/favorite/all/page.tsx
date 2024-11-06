import { SearchParams } from "../../../../objects/interfaces/searchParams.interface";
import FilterPageContainer from "../../../../components/custom/filters/FilterPageContainer";
import { Comedian } from "../../../../objects/classes/comedian/Comedian";
import BasicEntityCard from "../../../../components/custom/tables/cards/BasicEntityCard";

export default async function FavoriteComediansPage(props: {
    searchParams?: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer<Comedian>
                suspenseKey={
                    (searchParams?.query ?? "") + (searchParams?.page ?? 0)
                }
                renderItem={(entity) => {
                    return <BasicEntityCard entity={entity} />;
                }}
                results={[]}
                defaultNode={<div></div>}
            />
        </main>
    );
}
