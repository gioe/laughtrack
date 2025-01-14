import Image from "next/image";

interface BackgroundImageProps {
    imageUrl: string;
    alt: string;
}

export default function BackgroundImage({
    imageUrl,
    alt,
}: BackgroundImageProps) {
    return (
        <div className="absolute inset-0">
            <div className="relative w-full h-full">
                <div className="absolute inset-0 bg-black/30 z-10" />
                <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-black/70 z-10" />
                <Image
                    src={imageUrl}
                    alt={alt}
                    width={2880}
                    height={1772}
                    className="object-cover object-center w-full h-full"
                    priority
                    quality={90}
                />
            </div>
        </div>
    );
}
