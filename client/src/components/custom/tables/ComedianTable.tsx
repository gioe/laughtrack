'use client';

import React from "react";
import ComedianInfoCard from "./cards/ComedianInfoCard";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { GetComediansResponse } from "@/actions/comedians/getFavoriteComedians";
import { LineupItem } from "@/interfaces/lineupItem.interface";

interface ComedianTableProps {
    response: GetComediansResponse
}

const ComedianTable: React.FC<ComedianTableProps> = ({
    response,
}) => {

    return (
        <main className="flex flex-col pb-5">
            <section className="flex-grow flex-row pt-5 pl-5 pr-5">
                <div className="grid grid-cols-3 gap-4">
                    {response.comedians
                        .map((comedian: ComedianInterface | LineupItem) => {
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