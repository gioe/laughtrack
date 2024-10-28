'use client';

import React from "react";
import ComedianInfoCard from "./cards/FavoritableEntityCard";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import FavoritableEntityCard from "./cards/FavoritableEntityCard";

interface ComedianTableProps {
    comedians: ComedianInterface[]
}

const ComedianTable: React.FC<ComedianTableProps> = ({
    comedians,
}) => {

    return (
        <main className="flex flex-col pb-5">
            <section className="flex-grow flex-row pt-5 pl-5 pr-5">
                <div className="grid grid-cols-3 gap-4">
                    {comedians
                        .map((comedian: ComedianInterface) => {
                            return (
                                <FavoritableEntityCard
                                    key={comedian.name}
                                    type={Entity.Comedian}
                                    entity={comedian}
                                />
                            )
                        })}
                </div>
            </section>
        </main>

    )
}

export default ComedianTable;