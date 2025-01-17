"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import Image from "next/image";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
            {lineup.map((comedian, index) => (
                <div key={index} className="flex-shrink-0 snap-start">
                    <div className="relative w-32 h-32 rounded-lg overflow-hidden mb-2">
                        <Image
                            src={comedian.imageUrl}
                            alt={comedian.name}
                            fill
                            className="object-cover"
                        />
                    </div>
                    {comedian.name.split(" ").map((nameString) => {
                        return (
                            <p
                                key={nameString}
                                className="text-sm text-[#2D1810] font-medium text-center"
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
