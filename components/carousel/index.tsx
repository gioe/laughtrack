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
        <div className="flex space-x-3 overflow-scroll bg-ivory scrollbar-hide p-3 -ml-3">
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
