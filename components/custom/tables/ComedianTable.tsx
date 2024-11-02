"use client";

import React from "react";
import { ComedianInterface } from "../../../interfaces/comedian.interface";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { db } from "../../../database";
import FavoritableEntityCard from "./cards/FavoritableEntityCard";
import EntityType from "../icons/MiniEntityIcon";

export default async function ComedianTable({
    params,
}: {
    params?: SearchParams;
}) {
    const comedians = await db.comedians.getAllFavorites(1, params);

    return (
        <main className="flex flex-col pb-5">
            <section className="flex-grow flex-row pt-5 pl-5 pr-5">
                <div className="grid grid-cols-3 gap-4">
                    {comedians.map((comedian: ComedianInterface) => {
                        return (
                            <FavoritableEntityCard
                                key={comedian.name}
                                type={EntityType.Comedian}
                                entity={comedian}
                            />
                        );
                    })}
                </div>
            </section>
        </main>
    );
}
