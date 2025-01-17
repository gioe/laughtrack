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
        <div className="mx-24 my-12">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {gridComedians.map((comedian, index) => (
                    <ComedianGridCard
                        key={comedian.name}
                        entity={JSON.stringify(comedian)}
                    />
                ))}
            </div>
        </div>
    );
};

export default ComedianGrid;
