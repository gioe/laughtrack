"use server";

import CarouselCard from "../cards/carousel";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import { Comedian } from "../../objects/class/comedian/Comedian";

interface TrendingComedianCarouselProps {
    comedians: ComedianDTO[];
}
const TrendingComedianCarousel = ({
    comedians,
}: TrendingComedianCarouselProps) => {
    return (
        <div className="bg-green-500 flex flex-col items-center align-middle space-y-8 overflow-scroll scrollbar-hide lg:h-1/2 lg:mt-5 lg:space-x-8 lg:flex-row lg:space-y-0">
            {comedians.map((dto) => {
                const comedian = new Comedian(dto);
                return (
                    <CarouselCard
                        key={dto.name}
                        entity={JSON.stringify(comedian)}
                    />
                );
            })}
        </div>
    );
};

export default TrendingComedianCarousel;
