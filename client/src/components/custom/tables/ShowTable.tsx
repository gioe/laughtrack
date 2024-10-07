'use client';

import React, { useState } from "react";
import ShowInfoCard from "./cards/ShowInfoCard";
import Drawer from "../drawer/Drawer";
import FilterComponent, { PropertyFilter } from "../filters/FilterComponent";
import { ShowInterface } from "@/interfaces/show.interface";
import { PaginationComponent } from "../pagination/Pagination";
import { ShowProviderInterface } from "@/interfaces/dateContainer.interface";

export interface PaginatedShowInterface {
    entity: ShowProviderInterface;
    totalPages: number
}

interface ShowTableProps {
    response: PaginatedShowInterface;
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

const ShowTable: React.FC<ShowTableProps> = ({
    response
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
                        <FilterComponent propertyFilters={typeFilters} />
                        <PaginationComponent pageCount={response.totalPages} />
                    </div>
                )
            }
            <section className="flex-grow flex-row pt-14 px-6">
                <Drawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
                <div className="flex flex-col">
                    {response.entity.dates.length > 0 ? (
                        response.entity.dates
                            .map((show: ShowInterface) => {
                                return (
                                    <ShowInfoCard
                                        key={show.ticketLink}
                                        show={show}
                                    />
                                )
                            })
                    ) : (
                        <h2 className="font-bold text-5xl text-white pt-6">No upcoming shows. Check back later.</h2>
                    )}
                </div>
            </section>
        </main>


    )
}

export default ShowTable;