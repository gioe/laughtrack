"use server";

import { Comedian } from "../../../objects/class/comedian/Comedian";
import ComedianHeadshot from "../../image/comedian";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="flex flex-row gap-4 bg-black">
            {lineup.map((comedian: Comedian) => (
                <div
                    key={comedian.id.toString()}
                    className="hover:z-9 hover:scale-105 transform transition
duration-300 ease-out bg-blue-800 grid grid-cols-5 space-x-10"
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
