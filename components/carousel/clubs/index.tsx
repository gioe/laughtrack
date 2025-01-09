"use server";

import ClubCarouselCard from "../../cards/carousel/club";
import { ClubDTO } from "../../../objects/class/club/club.interface";
import { Club } from "../../../objects/class/club/Club";

interface TrendingClubsCarouselProps {
    clubs: ClubDTO[];
}

const TrendingClubsCarousel = ({ clubs }: TrendingClubsCarouselProps) => {
    return (
        <div className="max-w-full flex flex-col lg:grid lg:grid-rows-2 lg:grid-cols-3 overflow-scroll gap-x-6 gap-y-6 p-4">
            {clubs.map((dto) => {
                const club = new Club(dto);
                return (
                    <ClubCarouselCard
                        key={club.name}
                        entity={JSON.stringify(club)}
                    />
                );
            })}
        </div>
    );
};

export default TrendingClubsCarousel;
