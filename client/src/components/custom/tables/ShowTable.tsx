'use client';

import React, { useState } from "react";
import ShowInfoCard from "./cards/ShowInfoCard";
import Drawer from "../drawer/Drawer";
import FilterComponent, { PropertyFilter } from "../filters/FilterComponent";
import { ShowInterface } from "@/interfaces/show.interface";
import { PaginationComponent } from "../pagination/Pagination";
import { ShowProviderInterface } from "@/interfaces/dateContainer.interface";

export interface PaginatedShowPageInterface {
    entity: ShowProviderInterface;
    totalPages: number
}

interface ShowTableProps {
    response: PaginatedShowPageInterface;
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
    return (
        <main className="flex flex-col">
            <section className="flex flex-row items-center">
                { response.entity.dates.length > 1 && <FilterComponent propertyFilters={typeFilters} /> }
                { response.totalPages > 1 && <PaginationComponent pageCount={response.totalPages} /> }
            </section>
            <section className="flex-grow flex-row">
                <div className="flex flex-col">
                    { response.entity.dates.length > 0 ? (
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