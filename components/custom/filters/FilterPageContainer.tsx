"use client";

import { useState } from "react";
import { SideDrawerComponent } from "../drawer/SideDrawerComponent";
import { TablePaginationComponent } from "../pagination/TablePaginationComponent";
import { FunnelButton } from "./FunnelButton";
import GenericTable from "../tables/GenericTable";
import { SortOptionsComponent } from "../sort/SortOptionsComponent";
import { Entity } from "../../../objects/interfaces";
import EntityType from "../icons/MiniEntityIcon";
import ShowCard from "../cards/ShowCard";
import { Show } from "../../../objects/classes/show/Show";
import BasicEntityCard from "../cards/BasicEntityCard";

interface FilterPageContainerProps {
    resultString: string;
    defaultNode: React.ReactNode;
}

export default function FilterPageContainer({
    resultString,
    defaultNode,
}: FilterPageContainerProps) {
    const results = JSON.parse(resultString) as Entity[];

    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    return (
        <div className="bg-shark">
            <SideDrawerComponent
                isOpen={sideDrawerIsOpen}
                handleOpen={handleButtonClick}
            />

            <main className="mx-auto px-10 flex-item tems-end justify-end">
                <section aria-labelledby="search-parameter-options-section">
                    <div className="flex flex-row-reverse gap-4 items-center">
                        <FunnelButton handleClick={handleButtonClick} />
                        <SortOptionsComponent type={results[0].type} />
                        <TablePaginationComponent itemCount={results.length} />
                    </div>
                    <div className="grid grid-cols-1 gap-x-8 gap-y-10 lg:grid-cols-5">
                        <div className="lg:col-span-4">
                            <GenericTable
                                keyExtractor={(item) => item.id.toString()}
                                data={results}
                                defaultNode={defaultNode}
                                renderItem={(entity: Entity) => {
                                    {
                                        switch (entity.type) {
                                            case EntityType.Show:
                                                return (
                                                    <ShowCard
                                                        show={entity as Show}
                                                    />
                                                );
                                            default:
                                                return (
                                                    <BasicEntityCard
                                                        entity={entity}
                                                    />
                                                );
                                        }
                                    }
                                }}
                            />
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}
