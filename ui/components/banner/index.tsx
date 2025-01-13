"use client";

import Image from "next/image";
import { useState } from "react";

interface EntityBannerProps {
    identifier: string;
}

const EntityBanner = ({ identifier }: EntityBannerProps) => {
    const [src, setSrc] = useState<string>(`/images/banners/${identifier}.png`);

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
                    {decodeURI(identifier)}
                </h2>
            </div>
        </div>
    );
};

export default EntityBanner;
