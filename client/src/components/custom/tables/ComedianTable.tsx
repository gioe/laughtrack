'use client';

import React from "react";
import ComedianInfoCard from "./cards/ComedianInfoCard";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PropertyFilter } from "../filters/FilterComponent";
import { PaginationComponent } from "../pagination/Pagination";
import { GetComediansResponse } from "@/actions/comedians/getFavoriteComedians";
import TextSearchBar from "../search/TextSearchBar";

interface ComedianTableProps {
    response: GetComediansResponse
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

const ComedianTable: React.FC<ComedianTableProps> = ({
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
                    {response.comedians
                        .map((comedian: ComedianInterface) => {
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