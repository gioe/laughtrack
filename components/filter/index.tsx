"use client";

import React from "react";
import { useState } from "react";
import { SortParamComponent } from "../params/sort";
import { PageParamComponent } from "../params/page";
import { FunnelButton } from "../button/funnel";
import QueryParamComponent from "../params/query";
import { DrawerComponent } from "../drawer";
import { FilterParamComponent } from "../params/filter";
import { Filter } from "../../objects/class/tag/Filter";

interface TableFilterBarProps {
    totalItems: number;
    filtersString: string;
}

const TableFilterBar: React.FC<TableFilterBarProps> = ({
    totalItems,
    filtersString,
}) => {
    const filters = JSON.parse(filtersString) as Filter[];
    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    return (
        <div>
            <DrawerComponent
                isOpen={sideDrawerIsOpen}
                child={<FilterParamComponent filters={filters} />}
                handleOpen={handleButtonClick}
            />
            <div className="flex items-center gap-2 flex-row-reverse">
                <div className="flex items-center gap-4 justify-end">
                    <QueryParamComponent
                        inputPlaceholder={`Search for comedians`}
                    />
                    <SortParamComponent />
                    <PageParamComponent itemCount={totalItems} />
                    {filters.length > 0 && (
                        <FunnelButton handleClick={handleButtonClick} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default TableFilterBar;
