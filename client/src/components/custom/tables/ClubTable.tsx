'use client';

import React from "react";
import { ClubInterface } from "@/interfaces/club.interface";
import FavoritableEntityCard from "./cards/FavoritableEntityCard";

interface ClubTableProps {
    clubs: ClubInterface[]
}

const ClubTable: React.FC<ClubTableProps> = ({
    clubs
}) => {


    return (
        <main className="flex flex-col pb-5">
            <section className="flex-grow flex-row pt-5 pl-5 pr-5">
                <div className="grid grid-cols-3 gap-4">
                    {clubs
                        .map((club: ClubInterface) => {
                            return (
                                <FavoritableEntityCard
                                    key={club.name}
                                    type={Entity.Club}
                                    entity={club}
                                />
                            )
                        })}
                </div>
            </section>
        </main>

    )
}

export default ClubTable;