"use client";

import Image from "next/image";
import { useState } from "react";
import { ClubActivityDTO } from "../../../objects/class/club/club.interface";

interface ClubMarqueeProps {
    club: ClubActivityDTO;
    priority: boolean;
}

const ClubMarquee = ({ club }: ClubMarqueeProps) => {
    const imageUrl = `/images/club/square/${club.name}.png`;

    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <div className="size-20 flex-none rounded-xl relative">
            <Image
                fill
                src={src}
                alt={club.name}
                onError={onError}
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                priority
                style={{ borderRadius: "10%" }}
            />
        </div>
    );
};

export default ClubMarquee;
