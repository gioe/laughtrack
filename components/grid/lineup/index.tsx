"use client";

import { Comedian } from "../../../objects/class/comedian/Comedian";
import ComedianHeadshot from "../../image/comedian";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="grid grid-cols-5 gap-x-2 gap-y-2">
            {lineup.map((comedian: Comedian) => (
                <div
                    key={comedian.id.toString()}
                    className="hover:z-9 hover:scale-105 transform transition
duration-300 ease-out"
                >
                    <div className="flex flex-col items-center">
                        <ComedianHeadshot
                            priority={false}
                            comedian={comedian}
                            size="m"
                            type="rounded"
                        />
                        {comedian.name.split(" ").map((nameString) => {
                            return (
                                <h1
                                    key={nameString}
                                    className="font-fjalla text-center bg-red-500 w-full"
                                >
                                    {`${nameString}`}
                                </h1>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default LineupGrid;
