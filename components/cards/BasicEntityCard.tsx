"use client";

import { useState, useCallback } from "react";
import React from "react";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import Image from "next/image";
import Link from "next/link";
import useRegisterModal from "../../hooks/modalState/useRegisterModel";
import { useSession } from "next-auth/react";
import SocialMediaBar from "../social/SocialMediaBar";
import axios from "axios";
import { Entity } from "../../objects/interface";

interface BasicEntityCardProps {
    entity: Entity;
}

const BasicEntityCard: React.FC<BasicEntityCardProps> = ({ entity }) => {
    const [src, setSrc] = useState<string>(entity.cardImageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    const registerModal = useRegisterModal();
    const session = useSession();
    const [, /*isOpen */ setIsOpen] = useState(false);

    const [isFavorite, setIsFavorite] = useState(
        entity.isFavorite ? true : false,
    );

    const requireLogin = useCallback(() => {
        setIsOpen((value) => !value);
        registerModal.onOpen();
    }, [registerModal]);

    const handleFavoriteClick = () => {
        if (session.status == "authenticated") {
            axios
                .put(`/api/${entity.type.valueOf()}/favorite`, {
                    id: entity.id,
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

    return (
        <div className="flex flex-row bg-orange-500 rounded-xl shadow-md overflow-hidden md:max-w-2xl items-start">
            <div className="bg-green-800 flex-1">
                <Link href={`/${entity.type.valueOf()}/${entity.name}`}>
                    <div className="relative p-5 m-5 object-fill lg:h-40 lg:w-40 sm:h-40">
                        <Image
                            alt="Comedian"
                            src={src}
                            fill
                            onError={onError}
                            priority={false}
                            style={{ objectFit: "cover" }}
                            className="rounded-badge"
                        />
                    </div>
                </Link>
            </div>
            <div className="bg-red-900 flex-1">
                <div className="flex flex-col bg-yellow-400">
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

                    <h4 className="m:text-sm text-m text-left bg-blue-900">
                        {entity.name}
                    </h4>
                    {entity.socialData && (
                        <SocialMediaBar data={entity.socialData} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default BasicEntityCard;
