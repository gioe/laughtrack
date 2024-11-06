"use client";

import { useState } from "react";
import { SideDrawerComponent } from "../drawer/SideDrawerComponent";
import { TablePaginationComponent } from "../pagination/TablePaginationComponent";
import { FunnelButton } from "./FunnelButton";
import GenericTable from "../tables/GenericTable";
import { Entity } from "../../../objects/interfaces";
import { SortOptionsComponent } from "../../sort/SortOptionsComponent";

interface FilterPageContainerProps<T extends Entity> {
    results: T[];
    defaultNode: React.ReactNode;
    suspenseKey: string;
    renderItem: (item: T) => React.ReactNode;
}

export default function FilterPageContainer<T extends Entity>({
    results,
    defaultNode,
    suspenseKey,
    renderItem,
}: FilterPageContainerProps<T>) {
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
                            <GenericTable<T>
                                keyExtractor={(item) => item.id.toString()}
                                data={results}
                                defaultNode={defaultNode}
                                suspenseKey={suspenseKey}
                                renderItem={renderItem}
                            />
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}
