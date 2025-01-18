import Image from "next/image";
import React from "react";

interface ImageData {
    url: string;
    alt: string;
}

interface ImageGridProps {
    images: ImageData[];
    // Optional className for container customization
    className?: string;
}

const ImageGrid: React.FC<ImageGridProps> = ({ images, className = "" }) => {
    // Validate that exactly 3 images are provided
    if (images.length !== 1) {
        console.warn("ImageGrid component expects exactly 3 images");
        return null;
    }

    return (
        <div className={`grid grid-cols-3 gap-4 ${className}`}>
            {images.map((image, index) => (
                <div
                    key={`${image.url}-${index}`}
                    className="relative aspect-[3/4] overflow-hidden rounded-lg"
                >
                    <Image
                        src={image.url}
                        alt={image.alt}
                        fill
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-cover"
                        priority={index === 0} // Load the first image immediately
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 to-purple-900/40" />
                </div>
            ))}
        </div>
    );
};

export default ImageGrid;
