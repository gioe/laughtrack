'use client';

import React from "react";
import { PropertyFilter } from "../filters/FilterComponent";
import { PaginationComponent } from "../pagination/Pagination";
import TextSearchBar from "../search/TextSearchBar";
import ClubInfoCard from "./cards/ClubInfoCard";
import { ClubInterface } from "@/interfaces/club.interface";
import { GetClubsResponse } from "@/actions/clubs/getClubs";

interface ClubTableProps {
    response: GetClubsResponse
    selectedFilter?: string;
    query?: string;
}

const typeFilters: PropertyFilter[] = [
    {
        key: "date_time",
        label: "Date"
    },
    {
        key: "popularity_score",
        label: "Popularity"
    }
]

const ClubTable: React.FC<ClubTableProps> = ({
    response,
    query
}) => {


    return (
        <main className="flex flex-col pb-5">
            <div className="flex flex-row">
                <TextSearchBar query={query} />
                { response.totalPages > 1 && <PaginationComponent pageCount={response.totalPages} /> }
            </div>
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