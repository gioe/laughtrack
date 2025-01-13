"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Tooltip } from "@material-tailwind/react";
import { Comedian } from "@/objects/class/comedian/Comedian";

// Types
type AvatarShape = "rounded" | "circle";
type AvatarSize = "xs" | "s" | "m" | "l" | "xl";

interface ComedianHeadshotProps {
    comedian: Comedian;
    tooltip?: boolean;
    type?: AvatarShape;
    size?: AvatarSize;
    priority?: boolean;
    quality?: number;
    shouldAnimate?: boolean;
}

// Configuration
const AVATAR_STYLES = {
    shape: {
        rounded: { borderRadius: "20%" },
        circle: { borderRadius: "50%" },
    },
    size: {
        xs: "size-12",
        s: "size-16",
        m: "size-20",
        l: "size-40",
        xl: "size-52",
    },
} as const;

const ComedianHeadshot = ({
    comedian,
    tooltip = true,
    type = "rounded",
    size = "l",
    priority = true,
    shouldAnimate = true,
}: ComedianHeadshotProps) => {
    const [src, setSrc] = useState(
        comedian.cardImageUrl
            ? comedian.cardImageUrl
            : comedian.fallbackImageUrl,
    );

    const handleImageError = () => {
        setSrc(comedian.fallbackImageUrl);
    };

    // Determine if we need the pulsating border
    const shouldPulsate =
        (comedian.isAlias || comedian.isFavorite) && shouldAnimate;

    const getPulsateStyles = () => {
        if (!shouldPulsate) return "";

        return `
            before:absolute 
            before:inset-0 
            before:rounded-[inherit]
            before:border-8
            before:border-blue-400
            before:border-radius-50%
            before:animate-[pulse_2s_ease-in-out_infinite]
            ${comedian.isAlias && !comedian.isFavorite ? "before:border-purple-400" : ""}
            ${!comedian.isAlias && comedian.isFavorite ? "before:border-red-400" : ""}
        `;
    };

    const ImageComponent = () => (
        <div
            className={`
        relative 
        inline-block 
        hover:cursor-pointer 
        object-cover 
        object-center 
        ${AVATAR_STYLES.size[size]}
        ${getPulsateStyles()}
    `}
        >
            <Link
                href={`/comedian/${comedian.name}`}
                className="relative block h-full w-full"
            >
                <Image
                    fill
                    src={src.toString()}
                    alt={comedian.name}
                    onError={handleImageError}
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    priority={priority}
                    style={AVATAR_STYLES.shape[type]}
                />
            </Link>
        </div>
    );

    if (!tooltip) {
        return <ImageComponent />;
    }

    return (
        <Tooltip key={comedian.name} content={comedian.name}>
            <ImageComponent />
        </Tooltip>
    );
};

export default ComedianHeadshot;
