"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import { config } from "process";

const avatarConfig = {
    // Colors
    rounded: {
        borderRadius: "10%",
    },
    circle: {
        borderRadius: "50%",
    },

    // Sizes
    xs: "size-12",
    s: "size-16",
    m: "size-24",
    l: "size-40",
    xl: "size-52",

    isSpecial: "border-2 bg-rose-500",
};

interface ComedianHeadshotProps {
    comedian: Comedian;
    priority: boolean;
    type?: string;
    size?: string;
    quality?: string;
}

const ComedianHeadshot = ({
    comedian,
    type = "rounded",
    size = "l",
    quality = "isSpecial",
}: ComedianHeadshotProps) => {
    const destination = `/comedian/${comedian.name}`;
    const imageUrl = comedian.cardImageUrl;

    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <Tooltip key={comedian.name} content={comedian.name}>
            <div
                className={`
                     relative inline-block hover:cursor-pointer object-cover object-center ${avatarConfig[size]} ${avatarConfig[quality]}`}
            >
                <Link href={destination}>
                    <Image
                        fill
                        src={src}
                        alt={comedian.name}
                        onError={onError}
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        priority
                        style={avatarConfig[type]}
                    />
                </Link>
            </div>
        </Tooltip>
    );
};

export default ComedianHeadshot;
