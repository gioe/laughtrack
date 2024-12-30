"use client";

import SocialMediaBar from "../../../social/bar";
import ComedianHeadshot from "../../../image/comedian";
import { Comedian } from "../../../../objects/class/comedian/Comedian";

interface ComedianCarouselCardProps {
    entity: string;
}

const ComedianCarouselCard: React.FC<ComedianCarouselCardProps> = ({
    entity,
}) => {
    const parsedEntity = JSON.parse(entity) as Comedian;

    return (
        <div
            className="flex flex-col 
        items-center p-5 gap-8 bg-locust
         flex-none w-64 h-96 rounded-2xl"
        >
            <ComedianHeadshot priority entity={parsedEntity} />
            <div className="flex flex-col gap-1 w-full">
                <h1 className="font-fjalla text-pine-tree w-full text-center text-2xl">
                    {parsedEntity.name}
                </h1>

                {parsedEntity.showCount && (
                    <h1 className="text-pine-tree font-fjalla w-full text-center text-s">{`${parsedEntity.showCount ?? 0} upcoming shows`}</h1>
                )}
            </div>
            <div className="w-full flex-none">
                {parsedEntity.socialData && (
                    <SocialMediaBar data={parsedEntity.socialData} />
                )}
            </div>
        </div>
    );
};

export default ComedianCarouselCard;
