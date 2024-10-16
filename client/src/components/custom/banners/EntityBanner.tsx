'use client';

import Image from "next/image";
import SocialMediaBar from "../social/SocialMediaBar";
import {  ReactNode, useState } from "react";
import { BannerProviderInterface } from "@/interfaces/bannerProvider.interface";


interface EntityBannerProps {
    entity: BannerProviderInterface;
    menu: ReactNode,
}

const EntityBanner: React.FC<EntityBannerProps> = ({
    menu,
    entity
}) => {

    const [src, setSrc] = useState<string>(`/images/banners/${entity.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };

    return (
        <div className="relative h-[100px] sm:h-[200px] lg:h[300-px] xl:h-[400px] 2xl:h-[500-px]">
            <Image
                alt="Banner"
                src={src}
                fill
                priority
                placeholder="empty"
                sizes="80vw"
                onError={onError}
                style={{
                    objectFit: "cover"
                }}
            />
            <div className="absolute top-1/2 w-full text-center">
            <h2 className="font-bold text-5xl text-white pt-6">{entity.name}</h2>
            <SocialMediaBar data={entity.socialData} menu={menu}></SocialMediaBar>
            </div>
        </div>
    )
}

export default EntityBanner;