import ComedianCarouselCard from "../../../../../../components/cards/carousel/comedian";
import QueryableEntityTableContainer from "../../../../../../components/container";
import { Entity } from "../../../../../../objects/interface";

export default async function FavoriteComediansPage() {
    // const filters = await QueryHelper.storePageParams(
    //     props.searchParams,
    //     props.params,
    // );

    const renderFunction = (entity: Entity) => {
        return (
            <ComedianCarouselCard
                key={entity.name}
                entity={JSON.stringify(entity)}
            />
        );
    };
    return (
        <main className="flex-grow pt-5 bg-ivory">
            <QueryableEntityTableContainer
                totalEntities={1}
                entityCollectionString={""}
                cardRenderFunction={renderFunction}
                defaultNode={<div></div>}
            />
        </main>
    );
}
