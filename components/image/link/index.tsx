"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getPlaiceholder } from "plaiceholder";
import * as fsPromises from "fs/promises";
import path from "path";

const getImage = async (src: string) => {
    const buffer = await fsPromises.readFile(path.join("./public", src));
    const {
        metadata: { height, width },
        ...plaiceholder
    } = await getPlaiceholder(buffer, { size: 10 });

    return {
        ...plaiceholder,
        img: { src, height, width },
    };
};

interface LinkedImageProps {
    destination: string;
    imageUrl: string;
    alt: string;
}

async function LinkedImage({ destination, imageUrl, alt }: LinkedImageProps) {
    const getImage = async (imageUrl: string) => {
        const { base64, img } = await getImage(imageUrl);
        set;
    };

    useEffect(() => {
        getImage(imageUrl);
    }, [imageUrl]);

    const [img, setImage] = useState({
        src: imageUrl,
        height: 0,
        with: 0,
    });

    const onError = () => {
        setImage({
            ...img,
            src: `/images/logo.png`,
        });
    };

    return (
        <div className="object-fill">
            <Link href={destination}>
                <Image
                    src={src}
                    height={height}
                    width={width}
                    alt={alt}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    onError={onError}
                    priority={false}
                    style={{ objectFit: "cover" }}
                    blurDataURL={base64}
                    placeholder="blur"
                />
            </Link>
        </div>
    );
}

export default LinkedImage;
