'use client';

import React from "react";
import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowInterface } from "@/interfaces/show.interface";
import { ShowProviderInterface } from "@/interfaces/showProvider.interface";

export interface PaginatedShowPageInterface {
    entity: ShowProviderInterface;
    totalShows: number;
}

interface ShowTableProps {
    response: PaginatedShowPageInterface;
}

const ShowTable: React.FC<ShowTableProps> = ({
    response
}) => {
    return (
        <main className="flex flex-col">
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