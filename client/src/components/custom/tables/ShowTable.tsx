'use client';

import React, { useState } from "react";
import { ShowDetailsInterface } from "@/interfaces/show.interface";
import ShowInfoCard from "./cards/ShowInfoCard";
import ShowFilters from "../filters/ShowFilters";
import { PaginationComponent } from "../Pagination";
import SearchResultsFilters from "../filters/SearchResultsFilters";
import Drawer from "../drawer/Drawer";

interface ShowTableProps {
    shows: ShowDetailsInterface[];
}

const ShowTable: React.FC<ShowTableProps> = ({
    shows
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const toggleDrawer = () => {
        setIsDrawerOpen(!isDrawerOpen);
    };

    return (
        

        <main className="flex flex-col m-5">
            <div className="flex flex-row">
                <SearchResultsFilters cities={[]} />
                <PaginationComponent pageCount={10} />
            </div>
            <section className="flex-grow flex-row pt-14 px-6">
            <Drawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
                <div className="flex flex-col">
                    {shows.length > 0 ? (
                        shows
                            .map((show: ShowDetailsInterface) => {
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