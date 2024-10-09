'use client';

import { ComedianInterface } from "@/interfaces/comedian.interface";
import Image from "next/image"
import Link from "next/link";
import { useState } from "react";

interface LargeComedianIconProps {
    comedian: ComedianInterface;
}

export const LargeComedianIcon: React.FC<LargeComedianIconProps> = (
    { comedian }
) => {

    const [src, setSrc] = useState<string>(`/images/comedians/square/${comedian.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };

    return (
        <Link
        href={{
            pathname: `/comedian/${comedian.name}`,
        }}
    >
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <div className="relative h-80 w-80">
                <Image alt="Comedian"
                    src={src}
                    fill
                    priority={false}
                    sizes="80vw"
                    style={{objectFit:"cover"}}
                    className="rounded-2xl"
                    onError={onError}
                    >
                </Image>
            </div>

            <div>
                <h3 className="text-xl text-center mt-3">{comedian.name}</h3>
            </div>
            </div>
        </Link>
    )
}

export default LargeComedianIcon;