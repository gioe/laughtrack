"use client";

import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { useRegisterModal } from "@/hooks/modalState";
import { Comedian } from "@/objects/class/comedian/Comedian";
import Image from "next/image";
import Link from "next/link";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import SocialMediaBar from "../../social/bar";

interface ComedianGridCardProps {
    entity: string;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({ entity }) => {
    const registerModal = useRegisterModal();
    const session = useSession();
    const comedian = JSON.parse(entity) as Comedian;
    const [, setIsOpen] = useState(false);
    const [isFavorite, setIsFavorite] = useState(
        comedian.isFavorite ? true : false,
    );

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        // Prevent the link navigation when clicking the heart
        e.stopPropagation();

        if (session.status == "authenticated") {
            await makeRequest(APIRoutePath.ComedianFavorite, {
                method: RestAPIAction.POST,
                body: {
                    comedianId: comedian.uuid,
                    isFavorite,
                },
            }).then((data: { state: boolean }) => {
                setIsFavorite(data.state);
            });
        } else {
            requireLogin();
        }
    };

    const requireLogin = useCallback(() => {
        setIsOpen((value) => !value);
        registerModal.onOpen();
    }, [registerModal]);

    return (
        <div className="w-full rounded-xl items-center text-center overflow-hidden transition-transform duration-300 hover:scale-105 hover:cursor-pointer">
            <div className="relative rounded-xl aspect-square">
                <Link
                    href={`/comedian/${comedian.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={comedian.cardImageUrl.toString()}
                        alt={`${comedian.name}`}
                        fill
                        className="object-cover rounded-xl"
                        sizes="280px"
                        priority
                    />
                </Link>
                <button
                    onClick={handleFavoriteClick}
                    className="absolute top-2 right-2 p-1 hover:bg-black/10 rounded-full transition-colors z-10"
                >
                    {isFavorite ? (
                        <SolidHeart className="w-6 h-6 text-red-500" />
                    ) : (
                        <OutlineHeart className="w-6 h-6 text-red-500" />
                    )}
                </button>
            </div>

            {/* Artist Name */}
            <h2 className="text-[22px] font-bold mb-2 font-outfit">
                {comedian.name}
            </h2>

            {/* Shows Count */}
            <p className="text-[18px] text-gray-600 mb-6">{`${comedian.showCount ?? 0} upcoming shows`}</p>

            {/* Social Icons */}
            <div className="w-full">
                {comedian.socialData && (
                    <SocialMediaBar data={comedian.socialData} />
                )}
            </div>
        </div>
    );
};

export default ComedianGridCard;
