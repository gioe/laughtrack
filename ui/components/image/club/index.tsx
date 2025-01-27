"use client";

import Image from "next/image";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import Link from "next/link";
import { Club } from "@/objects/class/club/Club";

const PLACEHOLDER = "/images/club-placeholder.png";

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
    const [error, setError] = useState(false);

    const ImageComponent = () => (
        <div>
            <Link
                href={`/club/${club.name}`}
                className="relative block h-full w-full"
            >
                <div className="bg-black rounded-lg overflow-hidden aspect-square mb-4 relative">
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={club.name}
                        onError={() => setError(true)}
                        fill
                        className="object-cover"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                </div>
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
