'use client';

import React from "react";
import { ShowDetailsInterface } from "@/interfaces/show.interface";
import ShowInfoCard from "./cards/ShowInfoCard";

interface ShowTableProps {
    shows: ShowDetailsInterface[];
}

const ShowTable: React.FC<ShowTableProps> = ({
    shows
}) => {
    return (
        <div className="flex flex-col m-5">
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

    )
}

export default ShowTable;