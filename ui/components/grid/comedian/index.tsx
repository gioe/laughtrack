"use server";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";

interface ComedianGridProps {
    comedians: ComedianDTO[];
    className: string;
}
const ComedianGrid = ({ comedians, className }: ComedianGridProps) => {
    return (
        <div className="w-full">
            {comedians.length > 0 ? (
                <div className={className}>
                    {comedians.map((dto) => (
                        <ComedianGridCard
                            key={dto.name}
                            entity={JSON.stringify(dto)}
                        />
                    ))}
                </div>
            ) : (
                <h2 className="font-bold font-dmSans text-[60px] text-center pt-6">
                    No results. That person must not be funny enough.
                </h2>
            )}
        </div>
    );
};

export default ComedianGrid;
