import Link from "next/link";
import Image from "next/image";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { useState } from "react";
import { useFavorite } from "@/hooks/useFavorite";

interface ComedianHeadshotProps {
    comedian: Comedian;
    sizes?: string; // Make optional since lineup won't need it
    variant?: "grid" | "lineup";
    className?: string;
}

const PLACEHOLDER = "/images/comedian-placeholder.png";

const variantStyles = {
    grid: {
        container: "relative h-64",
        image: "object-cover object-center rounded-xl", // object-cover will crop/scale to fill
        favoriteButton: "absolute top-2 right-2",
    },
    lineup: {
        container: "relative h-[136px] w-[136px]",
        image: "object-cover object-center rounded-xl", // object-cover will crop/scale to fill
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
    const { isFavorite, handleFavoriteClick } = useFavorite({
        initialState: comedian.isFavorite ?? false,
        entityId: comedian.uuid,
    });

    console.log(isFavorite);
    const styles = variantStyles[variant];

    const imageProps =
        variant === "grid"
            ? {
                  fill: true,
                  sizes: sizes,
              }
            : {
                  width: 136,
                  height: 136,
              };

    return (
        <div className={`${styles.container} ${className}`}>
            <Link
                href={`/comedian/${comedian.name}`}
                className="block w-full h-full relative"
            >
                <Image
                    src={error ? PLACEHOLDER : comedian.imageUrl}
                    alt={`${comedian.name}`}
                    className={styles.image}
                    priority={false}
                    onError={() => setError(true)}
                    {...imageProps}
                />
            </Link>
            <button
                onClick={handleFavoriteClick}
                className={`${styles.favoriteButton} p-1 hover:bg-black/10 rounded-full transition-colors z-10`}
            >
                {isFavorite ? (
                    <SolidHeart className="w-6 h-6 text-red-500" />
                ) : (
                    <OutlineHeart className="w-6 h-6 text-red-500" />
                )}
            </button>
        </div>
    );
};

export default ComedianHeadshot;
