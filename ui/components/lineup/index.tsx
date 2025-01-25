"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import Image from "next/image";
import Link from "next/link";

interface LineupGridProps {
    lineup: Comedian[];
}
const LineupGrid = ({ lineup }: LineupGridProps) => {
    return (
        <div className="flex gap-4 overflow-x-auto pb-4 snap-x hover:cursor-pointer">
            {lineup.map((comedian, index) => (
                <div key={index} className="flex-shrink-0 snap-start">
                    <div className="relative w-32 h-32 rounded-lg overflow-hidden mb-2">
                        <Link
                            href={`/comedian/${comedian.name}`}
                            className="relative block h-full w-full"
                        >
                            <Image
                                src={comedian.imageUrl}
                                alt={comedian.name}
                                fill
                                className="object-cover"
                            />
                        </Link>
                    </div>
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
