"use client";

import { useState } from "react";
import { DrawerComponent } from "../drawer";
import { PageParamComponent } from "../params/page";
import { FunnelButton } from "../button/FunnelButton";
import { SortParamComponent } from "../params/sort";
import ShowCard from "../cards/showCard/ShowCard";
import { Entity } from "../../objects/interface";
import { Show } from "../../objects/class/show/Show";
import { FilterParamComponent } from "../params/filter";
import CarouselCard from "../cards/CarouselCard";
import Table from "../table";
import QueryParamComponent from "../params/query";
import { getSortOptionsForEntityType } from "../../util/sort";
import { EntityType } from "../../objects/enum";

interface QueryableEntityTableContainerProps {
    entityType: EntityType;
    entityCollectionString: string;
    defaultNode: React.ReactNode;
    totalEntities: number;
}

export default function QueryableEntityTableContainer({
    entityType,
    entityCollectionString,
    defaultNode,
    totalEntities,
}: QueryableEntityTableContainerProps) {
    const filteredEntityCollection = JSON.parse(
        entityCollectionString,
    ) as Entity[];
    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    const renderFunction = (entity: Entity) => {
        switch (entity.type) {
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
                child={<FilterParamComponent />}
                handleOpen={handleButtonClick}
            />

            <main className="mx-auto px-10 flex-item tems-end justify-end">
                <section aria-labelledby="search-parameter-options-section">
                    {totalEntities > 0 && (
                        <div className="flex-row">
                            {entityType !== EntityType.Show && (
                                <div className="flex-item">
                                    <QueryParamComponent
                                        inputPlaceholder={`Search by ${entityType.valueOf()} name`}
                                    />
                                </div>
                            )}
                            <div className="flex flex-row-reverse gap-4 items-center">
                                <FunnelButton handleClick={handleButtonClick} />
                                <SortParamComponent
                                    options={getSortOptionsForEntityType(
                                        entityType,
                                    )}
                                />
                                <PageParamComponent itemCount={totalEntities} />
                            </div>
                        </div>
                    )}
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
