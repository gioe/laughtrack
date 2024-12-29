"use client";

import SocialMediaBar from "../../social/bar";
import { CarouselEntity } from "../../../objects/interface";
import ComedianHeadshot from "../../image/comedian";

interface CarouselCardProps {
    entity: string;
}

const CarouselCard: React.FC<CarouselCardProps> = ({ entity }) => {
    const parsedEntity = JSON.parse(entity) as CarouselEntity;

    return (
        <div
            className="flex flex-col 
        items-center p-5 gap-8 bg-locust
         flex-none w-64 h-80 rounded-2xl"
        >
            <ComedianHeadshot priority entity={parsedEntity} />
            <div className="flex flex-col gap-3 w-full">
                <h1 className="font-fjalla text-brown-rust w-full text-center text-xl">
                    {parsedEntity.name}
                </h1>

                {parsedEntity.showCount && (
                    <h1 className="text-brown-rust font-fjalla w-full text-center text-xs">{`${parsedEntity.showCount ?? 0} upcoming shows`}</h1>
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

export default CarouselCard;
