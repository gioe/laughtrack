"use client";

import { useState } from "react";
import { DrawerComponent } from "../drawer";
import { PageParamComponent } from "../params/page";
import { FunnelButton } from "../button/FunnelButton";
import { SortParamComponent } from "../params/sort";
import EntityType from "../icons/MiniEntityIcon";
import ShowCard from "../cards/ShowCard";
import { Entity, SortOptionInterface } from "../../objects/interfaces";
import { Show } from "../../objects/classes/show/Show";
import Table from "../tables";
import { FilterParamComponent } from "../params/filter";
import CarouselCard from "../cards/CarouselCard";

interface QueryableTableContainerProps {
    resultString: string;
    defaultNode: React.ReactNode;
    sortOptions: SortOptionInterface[];
}

export default function QueryableTableContainer({
    resultString,
    defaultNode,
    sortOptions,
}: QueryableTableContainerProps) {
    const results = JSON.parse(resultString) as Entity[];
    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    const renderFunction = (entity: Entity) => {
        switch (entity.type) {
            case EntityType.Show:
                return <ShowCard show={entity as Show} />;
            default:
                return <CarouselCard key={entity.name} entity={entity} />;
        }
    };

    return (
        <div className="bg-shark">
            <DrawerComponent
                isOpen={sideDrawerIsOpen}
                child={<FilterParamComponent sections={[]} />}
                handleOpen={handleButtonClick}
            />

            <main className="mx-auto px-10 flex-item tems-end justify-end">
                <section aria-labelledby="search-parameter-options-section">
                    {results.length > 0 && (
                        <div className="flex flex-row-reverse gap-4 items-center">
                            <FunnelButton handleClick={handleButtonClick} />
                            <SortParamComponent options={sortOptions} />
                            <PageParamComponent itemCount={results.length} />
                        </div>
                    )}
                    <div className="grid grid-cols-1 gap-x-8 gap-y-10 lg:grid-cols-5">
                        <div className="lg:col-span-4">
                            <Table
                                keyExtractor={(item) => item.id.toString()}
                                data={results}
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
