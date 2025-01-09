"use client";

import Image from "next/image";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import Link from "next/link";
import { Club } from "../../../objects/class/club/Club";

const marqueeConfig = {
    // Colors
    rounded: {
        borderRadius: "25%",
    },
    circle: {
        borderRadius: "50%",
    },

    // Sizes
    s: "size-16",
    m: "size-24",
    l: "size-40",
    xl: "size-52",
};

interface ClubMarqueeProps {
    club: Club;
    priority: boolean;
    tooltip?: boolean;
    type?: string;
    size?: string;
}

const ClubMarquee = ({
    club,
    tooltip = true,
    type = "rounded",
    size = "m",
}: ClubMarqueeProps) => {
    const [src, setSrc] = useState(
        club.cardImageUrl ? club.cardImageUrl : club.fallbackImageUrl,
    );

    const handleImageError = () => {
        setSrc(club.fallbackImageUrl);
    };

    const ImageComponent = () => (
        <div
            className={`flex-none relative inline-block hover:cursor-pointer 
         object-cover object-center ${marqueeConfig[size]}`}
        >
            <Link
                href={`/club/${club.name}`}
                className="relative block h-full w-full"
            >
                <Image
                    fill
                    src={src.toString()}
                    alt={club.name}
                    onError={handleImageError}
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    priority
                    style={marqueeConfig[type]}
                />
            </Link>
        </div>
    );

    if (!tooltip) {
        return <ImageComponent />;
    }

    return (
        <Tooltip key={club.name} content={club.name}>
            <ImageComponent />
        </Tooltip>
    );
};

export default ClubMarquee;
