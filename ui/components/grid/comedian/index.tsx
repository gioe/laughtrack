"use server";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    comedians: ComedianDTO[];
}
const ComedianGrid = ({ comedians }: ComedianGridProps) => {
    return (
        <div className="mx-24 my-12">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {comedians.map((comedian, index) => (
                    <ComedianGridCard
                        key={index.toString()}
                        entity={JSON.stringify(comedian)}
                    />
                ))}
            </div>
        </div>
    );
};

export default ComedianGrid;
