import Link from "next/link";
import { Comedian } from "@/objects/class/comedian/Comedian";
import Image from "next/image";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";

interface ComedianHeadshotProps {
    comedian: Comedian;
    sizes: string;
    handleFavoriteClick: (e: React.MouseEvent) => void;
}

const ComedianLineupImage = ({
    comedian,
    handleFavoriteClick,
    sizes,
}: ComedianHeadshotProps) => {
    return (
        <div className="relative h-64">
            <Link
                href={`/comedian/${comedian.name}`}
                className="block w-full h-full relative"
            >
                <Image
                    src={comedian.imageUrl}
                    alt={`${comedian.name}`}
                    fill
                    className="object-cover rounded-xl"
                    sizes={sizes}
                    priority={false}
                    onError={() => {
                        console.log("THERE WAS AN ERROR WITH THE PHOTO");
                    }}
                />
            </Link>
            <button
                onClick={handleFavoriteClick}
                className="absolute top-2 right-2 p-1 hover:bg-black/10 rounded-full transition-colors z-10"
            >
                {comedian.isFavorite ? (
                    <SolidHeart className="w-6 h-6 text-red-500" />
                ) : (
                    <OutlineHeart className="w-6 h-6 text-red-500" />
                )}
            </button>
        </div>
    );
};

export default ComedianLineupImage;
