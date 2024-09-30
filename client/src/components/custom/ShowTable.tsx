import React from "react";
import { ShowDetailsInterface, ShowInterface } from "@/interfaces/show.interface";
import ShowInfoCard from "./ShowInfoCard";

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