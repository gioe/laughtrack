"use client";

import { Comedian } from "../../../objects/class/comedian/Comedian";
import ComedianHeadshot from "../../image/comedian";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="grid grid-rows-2 grid-flow-col gap-x-8 gap-y-8 grid-auto-rows">
            {lineup.map((comedian: Comedian) => (
                <div
                    key={comedian.id.toString()}
                    className="flex flex-col items-center"
                >
                    <div
                        className="hover:z-9 hover:scale-105 transform transition
duration-300 ease-out"
                    >
                        <ComedianHeadshot
                            priority={false}
                            tooltip={false}
                            comedian={comedian}
                            size="m"
                            type="rounded"
                        />
                    </div>

                    {comedian.name.split(" ").map((nameString) => {
                        return (
                            <h1
                                key={nameString}
                                className="font-fjalla text-center"
                            >
                                {`${nameString}`}
                            </h1>
                        );
                    })}
                </div>
            ))}
        </div>
    );
};

export default LineupGrid;
