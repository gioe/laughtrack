"use client";

import { Club } from "../../../../objects/class/club/Club";
import ClubMarquee from "../../../image/club";

interface ClubCarouselCardProps {
    entity: string;
}

const ClubCarouselCard: React.FC<ClubCarouselCardProps> = ({ entity }) => {
    const parsedEntity = JSON.parse(entity) as Club;

    return (
        <div
            className="flex
        items-center p-5 gap-8 bg-locust rounded-3xl 
        hover:scale-105 transform transition
        duration-300 ease-out hover:cursor-pointer"
        >
            <ClubMarquee priority club={parsedEntity} tooltip={false} />
            <div className="flex flex-col gap-3 w-full">
                <h1 className="font-fjalla text-pine-tree w-full text-center text-2xl">
                    {parsedEntity.name}
                </h1>

                {parsedEntity.count
                    ? parsedEntity.count > 0
                    : false && (
                          <h1 className="text-pine-tree font-fjalla w-full text-center text-m">{`${parsedEntity.count ?? 0} active comedians`}</h1>
                      )}
            </div>
        </div>
    );
};

export default ClubCarouselCard;
