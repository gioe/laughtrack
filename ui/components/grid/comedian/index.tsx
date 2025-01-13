"use server";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianCarouselCard from "@/ui/components/grid/comedian/card";
import Link from "next/link";

interface ComedianGridProps {
    contentString?: string;
    comedians?: ComedianDTO[];
}
const ComedianGrid = ({ comedians = [], contentString }: ComedianGridProps) => {
    const gridComedians = contentString
        ? (JSON.parse(contentString) as ComedianDTO[])
        : comedians;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 lg:grid-rows-2">
            {gridComedians.map((dto) => {
                const comedian = new Comedian(dto);
                return (
                    <ComedianCarouselCard
                        key={dto.name}
                        entity={JSON.stringify(comedian)}
                    />
                );
            })}
        </div>
    );
};

export default ComedianGrid;
