"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

interface LinkedImageProps {
    destination: string;
    imageUrl: string;
    alt: string;
    priority: boolean;
}

const LinkedImage = ({ destination, imageUrl, alt }: LinkedImageProps) => {
    const [src, setSrc] = useState(imageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <Link className={"size-32"} href={destination}>
            <Image
                width={208}
                height={208}
                src={src}
                alt={alt}
                onError={onError}
                priority
                style={{ objectFit: "cover" }}
            />
        </Link>
    );
};

export default LinkedImage;
