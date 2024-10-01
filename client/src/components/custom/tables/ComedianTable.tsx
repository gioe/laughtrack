'use client';

import React from "react";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import ComedianInfoCard from "./cards/ComedianInfoCard";

interface ComedianTableProps {
    comedians: ComedianInterface[];
}

const ComedianTable: React.FC<ComedianTableProps> = ({
    comedians
}) => {
    return (
        <div className="flex flex-col">
        {comedians
            .map((comedian: ComedianInterface) => {
                return (
                    <ComedianInfoCard
                        key={comedian.name}
                        userIsFollower={comedian.userIsFollower}
                        comedian={comedian}
                    />
                )
            })}
    </div>

    )
}

export default ComedianTable;