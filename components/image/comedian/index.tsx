"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Entity } from "../../../objects/interface";

interface ComedianHeadshotProps {
    entity: Entity;
    priority: boolean;
}

const ComedianHeadshot = ({ entity }: ComedianHeadshotProps) => {
    const destination = `/${entity.type.valueOf()}/${entity.name}`;
    const imageUrl = entity.cardImageUrl;
    const alt = entity.type.valueOf();

    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <div className="size-40 flex-none rounded-xl relative">
            <Link href={destination}>
                <Image
                    fill
                    src={src}
                    alt={alt}
                    onError={onError}
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    priority
                    style={{ borderRadius: "10%" }}
                />
            </Link>
        </div>
    );
};

export default ComedianHeadshot;
