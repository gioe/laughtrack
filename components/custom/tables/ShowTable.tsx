'use client';

import React from "react";
import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowInterface } from "../../../interfaces/show.interface";

interface ShowTableProps {
    shows: ShowInterface[];
}

const ShowTable: React.FC<ShowTableProps> = ({
    shows
}) => {
    return (
        <main className="flex flex-col">
            <section className="flex-grow flex-row">
                <div className="flex flex-col">
                    { shows.length > 0 ? (
                        shows
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