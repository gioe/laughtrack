import React from "react";
import ShowInfoCard from "./cards/ShowInfoCard";
import { db } from "../../../database";
import { ShowInterface } from "../../../interfaces";
import { SearchParams } from "../../../interfaces/searchParams.interface";

export default async function ShowTable({ params }: { params: SearchParams }) {
    const shows = await db.search.getHomeSearchResults(params);

    return (
        <main className="flex flex-col">
            <section className="flex-grow flex-row">
                <div className="flex flex-col">
                    {shows.length > 0 ? (
                        shows.map((show: ShowInterface) => {
                            return (
                                <ShowInfoCard
                                    key={show.ticketLink}
                                    show={show}
                                />
                            );
                        })
                    ) : (
                        <h2 className="font-bold text-5xl text-white pt-6">
                            No upcoming shows. Check back later.
                        </h2>
                    )}
                </div>
            </section>
        </main>
    );
}
