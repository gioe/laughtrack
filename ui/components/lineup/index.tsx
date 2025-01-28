"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import ComedianHeadshot from "../image/comedian";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="flex gap-4 overflow-x-auto pb-4 snap-x hover:cursor-pointer">
            {lineup.map((comedian, index) => (
                <div key={index} className="flex-shrink-0 snap-start">
                    <ComedianHeadshot comedian={comedian} variant="lineup" />
                    {comedian.name.split(" ").map((nameString) => {
                        return (
                            <p
                                key={nameString}
                                className="text-sm text-cedar font-semibold text-center font-dmSans text-[16px]"
                            >
                                {`${nameString}`}
                            </p>
                        );
                    })}
                </div>
            ))}
        </div>
    );
};

export default LineupGrid;
