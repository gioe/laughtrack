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

const LinkedImage = ({
    destination,
    imageUrl,
    alt,
    priority = false,
}: LinkedImageProps) => {
    const [src, setSrc] = useState<string>(imageUrl);
    const onError = () => {
        setSrc(`/images/logo.png`);
    };
    return (
        <div className="object-fill">
            <Link href={destination}>
                <Image
                    alt={alt}
                    src={src}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    onError={onError}
                    priority
                    style={{ objectFit: "cover" }}
                />
            </Link>
        </div>
    );
};

export default LinkedImage;
