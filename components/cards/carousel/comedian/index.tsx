"use client";

import SocialMediaBar from "../../../social/bar";
import ComedianHeadshot from "../../../image/comedian";
import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
import { useRegisterModal } from "../../../../hooks/modalState";
import axios from "axios";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";

interface ComedianCarouselCardProps {
    entity: string;
}

const ComedianCarouselCard: React.FC<ComedianCarouselCardProps> = ({
    entity,
}) => {
    const registerModal = useRegisterModal();
    const session = useSession();
    const parsedEntity = JSON.parse(entity) as Comedian;

    const [, /*isOpen */ setIsOpen] = useState(false);
    const [isFavorite, setIsFavorite] = useState(
        parsedEntity.isFavorite ? true : false,
    );

    const handleFavoriteClick = () => {
        if (session.status == "authenticated") {
            axios
                .put(`/api/comedian/favorite`, {
                    comedianId: parsedEntity.uuid,
                    isFavorite,
                })
                .then((response) => response.data)
                .then((data: { state: boolean }) => {
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
        <div
            className="flex flex-col 
        items-center p-5 gap-8 bg-locust rounded-3xl
        hover:scale-105 transform transition 
        duration-300 ease-out hover:cursor-pointer"
        >
            <div className="flex flex-row-reverse items-end">
                {isFavorite ? (
                    <SolidHeart
                        onClick={handleFavoriteClick}
                        className="h-7 cursor-pointer"
                    ></SolidHeart>
                ) : (
                    <OutlineHeart
                        onClick={handleFavoriteClick}
                        className="h-7 cursor-pointer"
                    />
                )}
            </div>
            <ComedianHeadshot
                priority
                comedian={parsedEntity}
                tooltip={false}
            />
            <div className="flex flex-col gap-1 w-full">
                <h1 className="font-fjalla text-pine-tree w-full text-center text-2xl">
                    {parsedEntity.name}
                </h1>

                {parsedEntity.showCount && (
                    <h1 className="text-pine-tree font-fjalla w-full text-center text-s">{`${parsedEntity.showCount ?? 0} upcoming shows`}</h1>
                )}
            </div>
            <div className="w-full">
                {parsedEntity.socialData && (
                    <SocialMediaBar data={parsedEntity.socialData} />
                )}
            </div>
        </div>
    );
};

export default ComedianCarouselCard;
