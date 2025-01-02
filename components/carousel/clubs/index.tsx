"use server";

import ClubCarouselCard from "../../cards/carousel/club";
import { ClubActivityDTO } from "../../../objects/class/club/club.interface";

interface TrendingClubsCarouselProps {
    clubs: ClubActivityDTO[];
}

const TrendingClubsCarousel = ({ clubs }: TrendingClubsCarouselProps) => {
    return (
        <div className="max-w-full flex flex-col lg:grid lg:grid-rows-2 lg:grid-cols-3 overflow-scroll gap-x-6 gap-y-6 p-4">
            {clubs.map((club) => {
                return <ClubCarouselCard key={club.name} club={club} />;
            })}
        </div>
    );
};

export default TrendingClubsCarousel;
