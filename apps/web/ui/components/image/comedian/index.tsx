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
    variant?: "grid" | "compactGrid" | "lineup";
    className?: string;
}

const variantStyles = {
    grid: {
        container: "relative w-full aspect-square",
        link: "block w-full h-full relative rounded-full overflow-hidden",
        image: "object-cover object-center",
        favoriteButton: "absolute top-[10%] right-[10%]",
        favoriteButtonPadding: "p-2.5",
        favoriteIcon: "w-6 h-6",
    },
    compactGrid: {
        container: "relative w-full aspect-square",
        link: "block w-full h-full relative rounded-full overflow-hidden",
        image: "object-cover object-center",
        favoriteButton: "absolute top-1 right-1",
        favoriteButtonPadding: "p-1.5",
        favoriteIcon: "w-4 h-4",
    },
    lineup: {
        container: "relative h-[136px] w-[136px]",
        link: "block w-full h-full relative",
        image: "object-cover object-center rounded-xl",
        favoriteButton: "absolute top-1 right-1",
        favoriteButtonPadding: "p-2.5",
        favoriteIcon: "w-6 h-6",
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

    const { isFavorite, handleFavoriteClick, isAuthenticated } = useFavorite({
        initialState: comedian.isFavorite,
        entityId: comedian.uuid,
    });

    const styles = variantStyles[variant];
    const showFallback = !comedian.hasImage || !comedian.imageUrl || error;

    const buttonBaseClasses = `${styles.favoriteButton} ${styles.favoriteButtonPadding} bg-black/20 hover:bg-black/30 rounded-full transition-all duration-200 z-10 shadow-md`;
    const buttonClasses = isAuthenticated
        ? buttonBaseClasses
        : `${buttonBaseClasses} border border-dashed border-white/70`;
    const buttonAriaLabel = isAuthenticated
        ? isFavorite
            ? `Remove ${comedian.name} from favorites`
            : `Add ${comedian.name} to favorites`
        : `Sign in to favorite ${comedian.name}`;

    return (
        <div className={`${styles.container} ${className}`}>
            <Link href={`/comedian/${comedian.name}`} className={styles.link}>
                {showFallback ? (
                    <ComedianAvatarFallback
                        name={comedian.name}
                        variant={variant === "compactGrid" ? "grid" : variant}
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
                    type="button"
                    onClick={handleFavoriteClick}
                    aria-label={buttonAriaLabel}
                    aria-pressed={isAuthenticated ? isFavorite : undefined}
                    className={buttonClasses}
                >
                    {isFavorite ? (
                        <SolidHeart
                            className={`${styles.favoriteIcon} text-red-500 drop-shadow-sm`}
                        />
                    ) : (
                        <OutlineHeart
                            className={`${styles.favoriteIcon} hover:text-red-500 drop-shadow-sm ${
                                isAuthenticated ? "text-white" : "text-white/80"
                            }`}
                        />
                    )}
                </button>
            )}
        </div>
    );
};

export default ComedianHeadshot;
