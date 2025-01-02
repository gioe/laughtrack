"use client";

import React from "react";
import { useState } from "react";
import { SortParamComponent } from "../params/sort";
import { PageParamComponent } from "../params/page";
import { FunnelButton } from "../button/funnel";
import QueryParamComponent from "../params/query";
import { useDataProvider } from "../../contexts/EntityPageDataProvider";
import { DrawerComponent } from "../drawer";
import { FilterParamComponent } from "../params/filter";

interface TableFilterBarProps {
    totalItems: number;
}

const TableFilterBar: React.FC<TableFilterBarProps> = ({ totalItems }) => {
    const { filters } = useDataProvider();
    const [sideDrawerIsOpen, setSideDrawerIsOpen] = useState(false);

    const handleButtonClick = (isOpen: boolean) => {
        setSideDrawerIsOpen(isOpen);
    };

    return (
        <div>
            <DrawerComponent
                isOpen={sideDrawerIsOpen}
                child={<FilterParamComponent />}
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
