'use client';

import React from "react";
import ComedianInfoCard from "./cards/ComedianInfoCard";
import Drawer from "../drawer/Drawer";
import { useState } from 'react';
import { ComedianInterface } from "@/interfaces/comedian.interface";
import FilterComponent, { PropertyFilter } from "../filters/FilterComponent";
import { PaginationComponent } from "../pagination/Pagination";
import { GetComediansResponse } from "@/actions/comedians/getFavoriteComedians";

interface ComedianTableProps {
    response: GetComediansResponse
    selectedFilter?: string;
}

const typeFilters: PropertyFilter[] = [
    {
        key: "date_time",
        label: "Date"
    },
    {
        key: "popularity_score",
        label: "Popularity"
    }
]

const ComedianTable: React.FC<ComedianTableProps> = ({
    response,
    selectedFilter,
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const toggleDrawer = () => {
        setIsDrawerOpen(!isDrawerOpen);
    };

    return (
        <main className="flex flex-col m-5">
                        {
                response.totalPages && (
                    <div className="flex flex-row">
                        <FilterComponent propertyFilters={typeFilters} selectedFilter={selectedFilter}/>
                        <PaginationComponent pageCount={response.totalPages} />
                    </div>
                )
            }
            <section className="flex-grow flex-row pt-14 px-6">
                <Drawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
                <div className="grid grid-cols-3 gap-4">
                    {response.comedians
                        .map((comedian: ComedianInterface) => {
                            return (
                                <ComedianInfoCard
                                    key={comedian.name}
                                    comedian={comedian}
                                />
                            )
                        })}
                </div>
            </section>
        </main>

    )
}

export default ComedianTable;