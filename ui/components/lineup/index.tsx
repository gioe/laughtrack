"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import ComedianHeadshot from "../image/comedian";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="relative">
            <div className="flex gap-4 overflow-x-auto pb-4 snap-x hover:cursor-pointer scrollbar-hide">
                {lineup.map((comedian, index) => (
                    <div
                        key={index}
                        className="flex-shrink-0 snap-start animate-[slideUp_500ms_ease-out,fadeIn_600ms_ease-out]"
                        style={{
                            animationDelay: `${index * 100}ms`,
                            opacity: 0,
                            animation: `slideUp 500ms ${index * 100}ms ease-out forwards, fadeIn 600ms ${index * 100}ms ease-out forwards`,
                        }}
                    >
                        <ComedianHeadshot
                            comedian={comedian}
                            variant="lineup"
                        />
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
            <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-l from-[#F5E6D3]/60 to-transparent pointer-events-none" />
        </div>
    );
};

export default LineupGrid;
