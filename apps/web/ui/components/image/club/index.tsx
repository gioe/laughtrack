"use client";

import Image from "next/image";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import { Club } from "@/objects/class/club/Club";
import Link from "next/link";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ClubMarqueeProps {
    club: Club;
    priority: boolean;
    tooltip?: boolean;
    type?: string;
    size?: string;
}

const ClubMarquee = ({ club, tooltip = true }: ClubMarqueeProps) => {
    const [error, setError] = useState(false);

    const imageContent = (
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
        return imageContent;
    }

    return (
        <Tooltip key={club.name} content={club.name}>
            {imageContent}
        </Tooltip>
    );
};

export default ClubMarquee;
