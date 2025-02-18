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
                <div className="max-w-7xl">
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                </div>
            )}
        </div>
    );
};

export default ComedianGrid;
