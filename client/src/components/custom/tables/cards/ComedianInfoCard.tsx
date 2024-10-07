'use client';

import { useState, useCallback } from 'react'
import React from "react";
import { HeartIcon as OutlineHeart } from "@heroicons/react/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/solid";
import Image from "next/image";
import Link from "next/link";
import { ComedianInterface } from '@/interfaces/comedian.interface';
import { addToFavorites } from '@/actions/addToFavorites';
import useLoginModal from '@/hooks/useLoginModal';
import useRegisterModal from '@/hooks/useRegisterModel';
import { useSession } from "next-auth/react";

interface ComedianInfoCardProps {
    comedian: ComedianInterface;
}

const ComedianInfoCard: React.FC<ComedianInfoCardProps> = ({
    comedian,
}) => {
    
    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();
    const session = useSession();
    const [isOpen, setIsOpen] = useState(false);

    const [isFavorite, setIsFavorite] = useState(comedian.favoriteId ? true : false)

    const requireLogin = useCallback(() => {
        setIsOpen((value => !value));
        registerModal.onOpen()
    }, [loginModal])


    const handleFavoriteClick = () => {
        if (session.status == 'authenticated') {
            addToFavorites(comedian.id ?? 0, isFavorite, session.data.accessToken).then((state: boolean) => {
                setIsFavorite(state)
            })
        }
        else {
            requireLogin()
        }
    }


    return (
        <div className="flex flex-row bg-orange-500 rounded-xl shadow-md overflow-hidden md:max-w-2xl items-start">
            <div className='bg-green-800 flex-1'>
                <Link
                    href={`/comedian/${comedian.name}`}
                >
                    <div className="relative p-5 m-5 object-fill lg:h-40 lg:w-40 sm:h-40">
                        <Image alt="Comedian"
                            src={`/images/comedians/square/${comedian.name}.png`}
                            fill
                            priority={false}
                            style={{ objectFit: "cover" }}
                            className="rounded-badge" />
                    </div>
                </Link>

            </div>
            <div className="bg-red-900 flex-1">
                <div className="flex flex-col bg-yellow-400">
                    <div className="flex flex-row-reverse items-end">
                        {
                            isFavorite ?
                                <SolidHeart onClick={handleFavoriteClick} className="h-7 cursor-pointer"></SolidHeart> :
                                <OutlineHeart onClick={handleFavoriteClick} className="h-7 cursor-pointer" />
                        }

                    </div>

                    <h4 className="m:text-sm text-m text-left bg-blue-900">{comedian.name}</h4>
                </div>
            </div>
        </div>
    )
}

export default ComedianInfoCard;