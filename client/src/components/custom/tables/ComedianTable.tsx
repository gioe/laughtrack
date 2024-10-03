'use client';

import React from "react";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import ComedianInfoCard from "./cards/ComedianInfoCard";
import { PaginationComponent } from "../pagination/Pagination";
import Drawer from "../drawer/Drawer";
import { useState } from 'react';
import TextSearchBar from "../search/TextSearchBar";

interface ComedianTableProps {
    comedians: ComedianInterface[]
}

const ComedianTable: React.FC<ComedianTableProps> = ({
    comedians
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const toggleDrawer = () => {
        setIsDrawerOpen(!isDrawerOpen);
    };

    return (
        <main className="flex flex-col m-5">
            <section className="flex-grow flex-row pt-14 px-6">
                <Drawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
                <div className="grid grid-cols-3 gap-4">
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
            </section>
        </main>

    )
}

export default ComedianTable;