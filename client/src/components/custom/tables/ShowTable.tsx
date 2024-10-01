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
        <div className="flex flex-col">
            {shows
                .map((show: ShowDetailsInterface) => {
                    return (
                        <ShowInfoCard
                            key={show.ticketLink}
                            show={show}
                        />
                    )
                })}
        </div>

    )
}

export default ShowTable;