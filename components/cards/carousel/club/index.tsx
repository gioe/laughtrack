"use client";

import { ClubActivityDTO } from "../../../../objects/class/club/club.interface";
import ClubMarquee from "../../../image/club";

interface ClubCarouselCardProps {
    club: ClubActivityDTO;
}

const ClubCarouselCard: React.FC<ClubCarouselCardProps> = ({ club }) => {
    return (
        <div
            className="flex
        items-center p-5 gap-8 bg-locust rounded-3xl 
        hover:scale-105 transform transition
        duration-300 ease-out hover:cursor-pointer"
        >
            <ClubMarquee priority name={club.name} tooltip={false} />
            <div className="flex flex-col gap-3 w-full">
                <h1 className="font-fjalla text-pine-tree w-full text-center text-2xl">
                    {club.name}
                </h1>

                {club.count && (
                    <h1 className="text-pine-tree font-fjalla w-full text-center text-m">{`${club.count ?? 0} active comedians`}</h1>
                )}
            </div>
        </div>
    );
};

export default ClubCarouselCard;
