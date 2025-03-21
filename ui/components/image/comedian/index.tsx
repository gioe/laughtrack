"use client";

import Link from "next/link";
import Image from "next/image";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { useState } from "react";
import { useFavorite } from "@/hooks/useFavorite";
import { getLocalCdnUrl } from "@/util/cdnUtil";

interface ComedianHeadshotProps {
    comedian: Comedian;
    sizes?: string;
    variant?: "grid" | "lineup";
    className?: string;
}

const PLACEHOLDER = getLocalCdnUrl("comedian-placeholder.png");
const ALIAS_PLACEHOLDER = getLocalCdnUrl("mystery-comedian-placeholder.png");

const variantStyles = {
    grid: {
        container: "relative w-full aspect-square",
        image: "object-cover object-center rounded-xl",
        favoriteButton: "absolute top-2 right-2",
    },
    lineup: {
        container: "relative h-[136px] w-[136px]",
        image: "object-cover object-center rounded-xl",
        favoriteButton: "absolute -top-1 -right-1 scale-75",
    },
};

const ComedianHeadshot = ({
    comedian,
    sizes,
    variant = "grid",
    className = "",
}: ComedianHeadshotProps) => {
    const [error, setError] = useState(false);
    const [loaded, setLoaded] = useState(false);

    const { isFavorite, handleFavoriteClick } = useFavorite({
        initialState: comedian.isFavorite,
        entityId: comedian.uuid,
    });

    const determineImage = () => {
        return error
            ? comedian.isAlias
                ? ALIAS_PLACEHOLDER
                : PLACEHOLDER
            : comedian.imageUrl;
    };

    const styles = variantStyles[variant];

    return (
        <div className={`${styles.container} ${className}`}>
            <Link
                href={`/comedian/${comedian.name}`}
                className="block w-full h-full relative"
            >
                <Image
                    src={determineImage()}
                    alt={`${comedian.name}`}
                    className={styles.image}
                    priority={false}
                    onError={() => setError(true)}
                    onLoad={() => setLoaded(true)}
                    fill={true}
                    sizes={sizes}
                />
            </Link>
            {loaded && (
                <button
                    onClick={handleFavoriteClick}
                    className={`${styles.favoriteButton} p-1 hover:bg-black/10 rounded-full transition-colors z-10`}
                >
                    {isFavorite ? (
                        <SolidHeart className="w-5 h-5 text-red-500" />
                    ) : (
                        <OutlineHeart className="w-5 h-5 text-red-500" />
                    )}
                </button>
            )}
        </div>
    );
};

export default ComedianHeadshot;
