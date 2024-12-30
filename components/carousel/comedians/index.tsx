"use server";

import ComedianCarouselCard from "../../cards/carousel/comedian";
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface";
import { Comedian } from "../../../objects/class/comedian/Comedian";

interface TrendingComedianCarouselProps {
    comedians: ComedianDTO[];
}
const TrendingComedianCarousel = ({
    comedians,
}: TrendingComedianCarouselProps) => {
    return (
        <div className="max-w-full flex overflow-scroll gap-10 p-4 scrollbar-default">
            {comedians.map((dto) => {
                const comedian = new Comedian(dto);
                return (
                    <ComedianCarouselCard
                        key={dto.name}
                        entity={JSON.stringify(comedian)}
                    />
                );
            })}
        </div>
    );
};

export default TrendingComedianCarousel;
