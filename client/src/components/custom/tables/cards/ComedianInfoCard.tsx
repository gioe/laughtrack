'use client';

import { useState, useCallback } from 'react'
import React from "react";
import { HeartIcon as OutlineHeart } from "@heroicons/react/24/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/24/solid";
import Image from "next/image";
import Link from "next/link";
import { ComedianInterface } from '@/interfaces/comedian.interface';
import useRegisterModal from '@/hooks/useRegisterModel';
import { useSession } from "next-auth/react";
import SocialMediaBar from '../../social/SocialMediaBar';
import { LineupItem } from '@/interfaces/lineupItem.interface';
import axios from 'axios';

interface ComedianInfoCardProps {
    comedian: ComedianInterface | LineupItem
}

const ComedianInfoCard: React.FC<ComedianInfoCardProps> = ({
    comedian,
}) => {
    
    const [src, setSrc] = useState<string>(`/images/comedians/square/${comedian.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };

    const registerModal = useRegisterModal();
    const session = useSession();
    const [/*isOpen */, setIsOpen] = useState(false);

    const [isFavorite, setIsFavorite] = useState(comedian.favoriteId ? true : false)

    const requireLogin = useCallback(() => {
        setIsOpen((value => !value));
        registerModal.onOpen()
    }, [registerModal])


    const handleFavoriteClick = () => {
        if (session.status == 'authenticated') {
            axios.put(`/api/comedian/${comedian.id}/avorite`, {
                isFavorite
            })
            .then((response: any) => {
                setIsFavorite(response.state)
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
                            src={src}
                            fill
                            onError={onError}
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
                    <SocialMediaBar data={comedian.socialData} menu={<div/>}/>
                    <h4 className="m:text-sm text-m text-left bg-white">{comedian.socialData?.popularityScore}</h4>
                </div>
            </div>
        </div>
    )
}

export default ComedianInfoCard;