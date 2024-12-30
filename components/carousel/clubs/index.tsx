"use server";

import ClubCarouselCard from "../../cards/carousel/club";
import { ClubActivityDTO } from "../../../objects/class/club/club.interface";

interface TrendingClubsCarouselProps {
    clubs: ClubActivityDTO[];
}
const TrendingClubsCarousel = ({ clubs }: TrendingClubsCarouselProps) => {
    return (
        <div className="max-w-full grid grid-rows-2 grid-cols-3 overflow-scroll gap-x-3 gap-y-3 p-4">
            {clubs.map((club) => {
                return <ClubCarouselCard key={club.name} club={club} />;
            })}
        </div>
    );
};

export default TrendingClubsCarousel;
