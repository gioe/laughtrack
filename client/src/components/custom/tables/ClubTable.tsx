'use client';

import React from "react";
import ClubInfoCard from "./cards/ClubInfoCard";
import { ClubInterface } from "@/interfaces/club.interface";
import { GetClubsResponse } from "@/actions/clubs/getClubs";

interface ClubTableProps {
    response: GetClubsResponse
}

const ClubTable: React.FC<ClubTableProps> = ({
    response
}) => {


    return (
        <main className="flex flex-col pb-5">
            <section className="flex-grow flex-row pt-5 pl-5 pr-5">
                <div className="grid grid-cols-3 gap-4">
                    {response.clubs
                        .map((club: ClubInterface) => {
                            return (
                                <ClubInfoCard
                                    key={club.name}
                                    club={club}
                                />
                            )
                        })}
                </div>
            </section>
        </main>

    )
}

export default ClubTable;