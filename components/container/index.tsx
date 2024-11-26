"use client";

import { useState } from "react";
import { DrawerComponent } from "../drawer";
import { PageParamComponent } from "../params/page";
import { FunnelButton } from "../button/FunnelButton";
import { SortParamComponent } from "../params/sort";
import ShowCard from "../cards/showCard/ShowCard";
import { Entity } from "../../objects/interface";
import { Show } from "../../objects/class/show/Show";
import CarouselCard from "../cards/CarouselCard";
import Table from "../table";
import QueryParamComponent from "../params/query";
import { getSortOptionsForEntityType } from "../../util/sort";
import { EntityType } from "../../objects/enum";
import { useFilterContext } from "../../contexts/FilterContext";
import { FilterParamComponent } from "../params/filter";

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
    const { type, filters } = useFilterContext();

    const filteredEntityCollection = JSON.parse(
        entityCollectionString,
    ) as Entity[];
    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    const renderFunction = (entity: Entity) => {
        switch (type) {
            case EntityType.Show:
                return <ShowCard key={entity.name} show={entity as Show} />;
            default:
                return <CarouselCard key={entity.name} entity={entity} />;
        }
    };

    return (
        <div className="bg-shark">
            <DrawerComponent
                isOpen={sideDrawerIsOpen}
                child={
                    filters.length > 0 && (
                        <FilterParamComponent containers={filters} />
                    )
                }
                handleOpen={handleButtonClick}
            />

            <main className="mx-auto px-10 flex-item tems-end justify-end">
                <section aria-labelledby="search-parameter-options-section">
                    <div className="flex-row">
                        {type !== EntityType.Show && (
                            <div className="flex-item">
                                <QueryParamComponent
                                    inputPlaceholder={`Search by ${type.valueOf()} name`}
                                />
                            </div>
                        )}
                        <div className="flex flex-row-reverse gap-4 items-center">
                            {filters.length > 0 && (
                                <FunnelButton handleClick={handleButtonClick} />
                            )}
                            <SortParamComponent
                                options={getSortOptionsForEntityType(type)}
                            />
                            <PageParamComponent itemCount={totalEntities} />
                        </div>
                    </div>
                    <div className="grid grid-cols-1 gap-x-8 gap-y-10 lg:grid-cols-5">
                        <div className="lg:col-span-4">
                            <Table
                                keyExtractor={(item) => item.id.toString()}
                                data={filteredEntityCollection}
                                defaultNode={defaultNode}
                                renderItem={renderFunction}
                            />
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}
