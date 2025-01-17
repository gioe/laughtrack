"use server";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    contentString: string;
}
const ComedianGrid = ({ contentString }: ComedianGridProps) => {
    const gridComedians = JSON.parse(contentString) as ComedianDTO[];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-20 gap-y-20">
            {gridComedians.map((dto) => {
                return (
                    <ComedianGridCard
                        key={dto.name}
                        entity={JSON.stringify(dto)}
                    />
                );
            })}
        </div>
    );
};

export default ComedianGrid;
