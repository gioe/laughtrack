"use client";

import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { useFavoriteRegisterModal } from "@/hooks/modalState";
import { Comedian } from "@/objects/class/comedian/Comedian";
import Image from "next/image";
import Link from "next/link";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import SocialMediaBar from "../../social/bar";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

interface ComedianGridCardProps {
    entity: string;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({ entity }) => {
    const registerModal = useFavoriteRegisterModal();
    const session = useSession();
    const comedian = new Comedian(JSON.parse(entity) as ComedianDTO);
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
        <div className="bg-white rounded-xl overflow-hidden">
            {/* Image Container */}
            <div className="relative h-64">
                <Link
                    href={`/comedian/${comedian.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={comedian.imageUrl}
                        alt={`${comedian.name}`}
                        fill
                        className="object-cover"
                        sizes="(max-width: 768px) 100vw,
                               (max-width: 1200px) 50vw,
                               25vw"
                        priority={false}
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

            {/* Content Container */}
            <div className="mt-4">
                <h2 className="text-[22px] font-bold mb-1 font-outfit">
                    {comedian.name}
                </h2>

                <p className="text-[18px] text-gray-600 mb-4">
                    {`${comedian.showCount ?? 0} upcoming shows`}
                </p>

                <div className="w-full">
                    {comedian.socialData && (
                        <SocialMediaBar data={comedian.socialData} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default ComedianGridCard;
