import Image from "next/image";

const Banner = () => {
    return (
        <div className="relative h-[300px] sm:h-[400px] lg:h[500-px] xl:h-[600px] 2xl:h-[700-px]">
            <Image
                alt="Banner"
                src="/images/banner.png"
                fill
                priority
                sizes="80vw"
                style={{
                    objectFit: "cover"
                }}
            />
        </div>
    )
}

export default Banner;