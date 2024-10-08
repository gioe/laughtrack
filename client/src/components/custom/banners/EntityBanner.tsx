import Image from "next/image";
import SocialMediaBar from "../social/SocialMediaBar";
import { ShowProviderInterface } from "@/interfaces/dateContainer.interface";

interface EntityBannerProps {
    entity: ShowProviderInterface;
}

const EntityBanner: React.FC<EntityBannerProps> = ({
    entity
}) => {
    return (
        <div className="relative h-[300px] sm:h-[400px] lg:h[500-px] xl:h-[600px] 2xl:h-[700-px]">
            <Image
                alt="Banner"
                src={`/images/comedians/banner/${entity.name}.png`}
                fill
                priority
                sizes="80vw"
                style={{
                    objectFit: "cover"
                }}
            />
            <div className="absolute top-1/2 w-full text-center">
            <h2 className="font-bold text-5xl text-white pt-6">{entity.name}</h2>
            <SocialMediaBar data={entity.socialData}></SocialMediaBar>

            </div>
        </div>
    )
}

export default EntityBanner;