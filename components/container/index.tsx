"use client";

import { useState } from "react";
import { DrawerComponent } from "../drawer";
import { PageParamComponent } from "../params/page";
import { SortParamComponent } from "../params/sort";
import ShowCard from "../cards/show";
import { Entity } from "../../objects/interface";
import { Show } from "../../objects/class/show/Show";
import CarouselCard from "../cards/carousel/comedian";
import Table from "../table";
import QueryParamComponent from "../params/query";
import { EntityType } from "../../objects/enum";
import { FilterParamComponent } from "../params/filter";
import { useDataProvider } from "../../contexts/EntityPageDataProvider";
import { usePageContext } from "../../contexts/PageEntityProvider";
import { FunnelButton } from "../button/funnel";

interface QueryableEntityTableContainerProps {
    entityCollectionString: string;
    defaultNode: React.ReactNode;
    totalEntities: number;
}

export default function QueryableEntityTableContainer({
    entityCollectionString,
    defaultNode,
    totalEntities,
}: QueryableEntityTableContainerProps) {
    const { primaryEntity, secondaryEntity } = usePageContext();
    const { filters } = useDataProvider();

    const filteredEntityCollection = JSON.parse(
        entityCollectionString,
    ) as Entity[];

    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    const renderFunction = (entity: Entity) => {
        switch (secondaryEntity) {
            case EntityType.Show:
                return (
                    <ShowCard
                        key={`${entity.name}-${entity.id}`}
                        show={entity as Show}
                    />
                );
            default:
                return (
                    <CarouselCard
                        key={entity.name}
                        entity={JSON.stringify(entity)}
                    />
                );
        }
    };

    return (
        <main className="mx-auto px-10 flex-item items-end justify-end">
            <DrawerComponent
                isOpen={sideDrawerIsOpen}
                child={<FilterParamComponent />}
                handleOpen={handleButtonClick}
            />
            <section aria-labelledby="search-parameter-options-section">
                <div className="flex items-center gap-4 justify-end">
                    <QueryParamComponent
                        inputPlaceholder={`Search for comedians`}
                    />
                    <SortParamComponent />
                    <PageParamComponent itemCount={totalEntities} />
                    {filters.length > 0 && (
                        <FunnelButton handleClick={handleButtonClick} />
                    )}
                </div>
            </section>
            <section>
                <Table
                    keyExtractor={(item) => item.id.toString()}
                    data={filteredEntityCollection}
                    defaultNode={defaultNode}
                    renderItem={renderFunction}
                />
            </section>
        </main>
    );
}
