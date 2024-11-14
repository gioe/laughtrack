"use client";

import Image from "next/image";
import SocialMediaBar from "../social/SocialMediaBar";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { Menu } from "../menu";
import { getMenuItemsForEntityType } from "../../util/menu";
import { Entity } from "../../objects/interface";

interface EntityBannerProps {
    entityString: string;
}

const EntityBanner: React.FC<EntityBannerProps> = ({ entityString }) => {
    const entity = JSON.parse(entityString) as Entity;
    const menuItems = getMenuItemsForEntityType(entity.type);
    const session = useSession();
    const shouldShowMenu = session.data?.user.role == "admin";

    const [src, setSrc] = useState<string>(entity.bannerImageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <div className="relative h-[400px] sm:h-[400px] lg:h[300-px] xl:h-[400px] 2xl:h-[500-px]">
            <Image
                alt="Banner"
                src={src}
                fill
                priority
                placeholder="empty"
                sizes="80vw"
                onError={onError}
                style={{
                    objectFit: "cover",
                }}
            />
            <div className="absolute top-1/2 w-full text-center">
                <h2 className="font-bold sm:text-4xl m:text-4xl lg:text-4xl xl:text-4xl 2xl:text-4xl text-white pt-6 pb-6">
                    {entity.name}
                </h2>
                {entity.socialData && (
                    <SocialMediaBar data={entity.socialData} />
                )}
                {shouldShowMenu && menuItems && (
                    <Menu providedItems={menuItems} />
                )}
            </div>
        </div>
    );
};

export default EntityBanner;
