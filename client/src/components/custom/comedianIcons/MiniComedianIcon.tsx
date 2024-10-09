'use client';


import { ComedianInterface } from "@/interfaces/comedian.interface";
import { LineupItem } from "@/interfaces/comedian.interface copy";
import Image from "next/image"
import Link from "next/link";
import { useState } from "react";

interface MiniComedianIconProps {
    comedian: ComedianInterface | LineupItem;
}

export const MiniComedianIcon: React.FC<MiniComedianIconProps> = (
    { comedian }
) => {

    const [src, setSrc] = useState<string>(`/images/comedians/square/${comedian.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };

    return (
        <div className="flex flex-col w-20">
        <Link
            href={`/comedian/${comedian.name}`}
        >
            <div className="cursor-pointer hover:scale-105 t
            ransform transition duration-300 ease-out text-center">
                <div className="relative h-20 w-20">
                    <Image alt="Comedian"
                        src={src}
                        fill
                        priority={false}
                        style={{ objectFit: "cover" }}
                        className="rounded-2xl"
                        onError={onError}
                        >
                    </Image>
                </div>

                <div>
                    <p className="md:text-sm text-xs text-gray-500 text-light font-semibold text-center">{comedian.name}</p>
                </div>
            </div>
        </Link>
        </div>

    )
}

export default MiniComedianIcon;