"use client";

import Image from "next/image";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import Link from "next/link";

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
    name: string;
    priority: boolean;
    tooltip?: boolean;
    type?: string;
    size?: string;
}

const ClubMarquee = ({
    name,
    tooltip = true,
    type = "rounded",
    size = "m",
}: ClubMarqueeProps) => {
    const destination = `/club/${name}`;
    const imageUrl = `/images/club/square/${name}.png`;

    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return tooltip ? (
        <Tooltip placement={"top"} key={name} content={name}>
            <div
                className={`flex-none
                     relative inline-block hover:cursor-pointer 
                     object-cover object-center ${marqueeConfig[size]}`}
            >
                <Link href={destination}>
                    <Image
                        fill
                        src={src}
                        alt={name}
                        onError={onError}
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        priority
                        style={marqueeConfig[type]}
                    />
                </Link>
            </div>
        </Tooltip>
    ) : (
        <div
            className={`flex-none
             relative inline-block hover:cursor-pointer 
             object-cover object-center ${marqueeConfig[size]}`}
        >
            <Link href={destination}>
                <Image
                    fill
                    src={src}
                    alt={name}
                    onError={onError}
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    priority
                    style={marqueeConfig[type]}
                />
            </Link>
        </div>
    );
};

export default ClubMarquee;
