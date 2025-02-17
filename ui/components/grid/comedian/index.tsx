"use server";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    comedians: ComedianDTO[];
    className: string;
}
const ComedianGrid = ({ comedians, className }: ComedianGridProps) => {
    return (
        <div className="mx-24 mt-12">
            <div className={className}>
                {comedians.map((dto) => (
                    <ComedianGridCard
                        key={dto.name}
                        entity={JSON.stringify(dto)}
                    />
                ))}
            </div>
        </div>
    );
};

export default ComedianGrid;
