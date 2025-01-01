"use client";

import Image from "next/image";
import { useState } from "react";
import { ClubActivityDTO } from "../../../objects/class/club/club.interface";
import { Tooltip } from "@material-tailwind/react";
import Link from "next/link";

const marqueeConfig = {
    // Colors
    rounded: {
        borderRadius: "10%",
    },
    circle: {
        borderRadius: "50%",
    },

    // Sizes
    s: "size-12",
    m: "size-20",
    l: "size-40",
    xl: "size-52",
};

interface ClubMarqueeProps {
    club: ClubActivityDTO;
    priority: boolean;
    type?: string;
    size?: string;
}

const ClubMarquee = ({
    club,
    type = "rounded",
    size = "m",
}: ClubMarqueeProps) => {
    const destination = `/club/${club.name}`;
    const imageUrl = `/images/club/square/${club.name}.png`;

    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <Tooltip key={club.name} content={club.name}>
            <div
                className={`flex-none
                     relative inline-block hover:cursor-pointer 
                     object-cover object-center ${marqueeConfig[size]}`}
            >
                <Link href={destination}>
                    <Image
                        fill
                        src={src}
                        alt={club.name}
                        onError={onError}
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        priority
                        style={marqueeConfig[type]}
                    />
                </Link>
            </div>
        </Tooltip>
    );
};

export default ClubMarquee;
