"use client";

import Link from "next/link";
import Image from "next/image";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { useState } from "react";
import { useFavorite } from "@/hooks/useFavorite";
import ComedianAvatarFallback from "./fallback";

interface ComedianHeadshotProps {
    comedian: Comedian;
    sizes?: string;
    variant?: "grid" | "lineup";
    className?: string;
}

const variantStyles = {
    grid: {
        container: "relative w-full aspect-square",
        link: "block w-full h-full relative rounded-full overflow-hidden",
        image: "object-cover object-center",
        favoriteButton: "absolute top-[10%] right-[10%]",
    },
    lineup: {
        container: "relative h-[136px] w-[136px]",
        link: "block w-full h-full relative",
        image: "object-cover object-center rounded-xl",
        favoriteButton: "absolute top-1 right-1",
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

    const styles = variantStyles[variant];
    const showFallback = !comedian.hasImage || !comedian.imageUrl || error;

    return (
        <div className={`${styles.container} ${className}`}>
            <Link href={`/comedian/${comedian.name}`} className={styles.link}>
                {showFallback ? (
                    <ComedianAvatarFallback
                        name={comedian.name}
                        variant={variant}
                    />
                ) : (
                    <Image
                        src={comedian.imageUrl}
                        alt={`${comedian.name}`}
                        className={styles.image}
                        priority={false}
                        onError={() => setError(true)}
                        onLoad={() => setLoaded(true)}
                        fill={true}
                        sizes={sizes}
                    />
                )}
            </Link>
            {(showFallback || loaded) && (
                <button
                    onClick={handleFavoriteClick}
                    className={`${styles.favoriteButton} p-2.5 bg-black/20 hover:bg-black/30 rounded-full transition-all duration-200 z-10 shadow-md`}
                >
                    {isFavorite ? (
                        <SolidHeart className="w-6 h-6 text-red-500 drop-shadow-sm" />
                    ) : (
                        <OutlineHeart className="w-6 h-6 text-white hover:text-red-500 drop-shadow-sm" />
                    )}
                </button>
            )}
        </div>
    );
};

export default ComedianHeadshot;
