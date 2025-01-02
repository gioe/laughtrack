"use client";

import { useState } from "react";
import { DrawerComponent } from "../drawer";
import { PageParamComponent } from "../params/page";
import { SortParamComponent } from "../params/sort";
import { Entity } from "../../objects/interface";
import Table from "../table";
import QueryParamComponent from "../params/query";
import { FilterParamComponent } from "../params/filter";
import { useDataProvider } from "../../contexts/EntityPageDataProvider";
import { FunnelButton } from "../button/funnel";

interface QueryableEntityTableContainerProps {
    entityCollectionString: string;
    defaultNode: React.ReactNode;
    totalEntities: number;
    cardRenderFunction: (entity: Entity) => JSX.Element;
}

export default function QueryableEntityTableContainer({
    entityCollectionString,
    defaultNode,
    totalEntities,
    cardRenderFunction,
}: QueryableEntityTableContainerProps) {
    const { filters } = useDataProvider();

    const filteredEntityCollection = JSON.parse(
        entityCollectionString,
    ) as Entity[];

    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
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
                    renderItem={cardRenderFunction}
                />
            </section>
        </main>
    );
}
