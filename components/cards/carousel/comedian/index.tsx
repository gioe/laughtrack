"use client";

import SocialMediaBar from "../../../social/bar";
import ComedianHeadshot from "../../../image/comedian";
import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
import { useRegisterModal } from "../../../../hooks/modalState";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import { APIRoutePath } from "../../../../objects/enum";
import { RestAPIAction } from "../../../../objects/enum/restApiAction";
import { makeRequest } from "../../../../util/actions/makeRequest";

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

    const handleFavoriteClick = async () => {
        if (session.status == "authenticated") {
            await makeRequest(APIRoutePath.ComedianFavorite, {
                method: RestAPIAction.POST,
                body: {
                    comedianId: parsedEntity.uuid,
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
        <div
            className="flex flex-col 
        items-center p-5 gap-8 bg-locust rounded-3xl
        hover:scale-105 transform transition 
        duration-300 ease-out hover:cursor-pointer"
        >
            <div className="relative inline-block">
                <ComedianHeadshot
                    shouldAnimate={false}
                    priority
                    comedian={parsedEntity}
                    tooltip={false}
                />
                <button
                    onClick={handleFavoriteClick}
                    className="absolute top-2 right-2 p-1 hover:bg-black/10 rounded-full transition-colors"
                >
                    {isFavorite ? (
                        <SolidHeart className="w-6 h-6 text-red-500" />
                    ) : (
                        <OutlineHeart className="w-6 h-6 text-ivory" />
                    )}
                </button>
            </div>
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
