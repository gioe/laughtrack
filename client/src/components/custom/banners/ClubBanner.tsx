import Image from "next/image";
import { ClubDetailsInterface } from "@/interfaces/club.interface";
import SocialMediaBar from "../social/SocialMediaBar";

interface ClubBannerProps {
    club: ClubDetailsInterface;
}

const ClubBanner: React.FC<ClubBannerProps> = ({
    club
}) => {
    return (
        <div className="relative h-[300px] sm:h-[400px] lg:h[500-px] xl:h-[600px] 2xl:h-[700-px]">
            <Image
                alt="Banner"
                src={`/images/clubs/banner/${club.name}.png`}
                fill
                priority
                sizes="80vw"
                style={{
                    objectFit: "cover"
                }}
            />
            <div className="absolute top-1/2 w-full text-center">
            <h2 className="font-bold text-5xl text-white pt-6">{club.name}</h2>
            <SocialMediaBar data={{
                website: club.baseUrl
            }}></SocialMediaBar>

            </div>
        </div>
    )
}

export default ClubBanner;