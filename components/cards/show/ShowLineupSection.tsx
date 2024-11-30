"use client";

import React from "react";
import { MiniEntityIcon } from "../../icons/MiniEntityIcon";
import Link from "next/link";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import { Entity } from "../../../objects/interface";

interface ShowCardProps {
    showName: string;
    lineup: Entity[];
}

const ShowLineupSection: React.FC<ShowCardProps> = ({ showName, lineup }) => {
    return (
        <section className="flex flex-col px-10">
            <Link href={`/show/${showName}`}>
                <h4 className="text-m text-center">{showName ?? ""}</h4>
            </Link>
            <div className="grid grid-cols-4 md:grid-cols-4 lg:grid-cols-4 gap-4 m-3 overflow-scrollscrollbar-hide">
                {lineup.map((comedian: Comedian) => (
                    <MiniEntityIcon key={comedian.name} entity={comedian} />
                ))}
            </div>
        </section>
    );
};

export default ShowLineupSection;
