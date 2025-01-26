"use server";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    comedians: ComedianDTO[];
    className: string;
}
const ComedianGrid = ({ comedians, className }: ComedianGridProps) => {
    return (
        <div className="mx-24 my-12">
            <div className={className}>
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
