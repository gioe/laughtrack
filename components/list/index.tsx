"use server";

import CarouselCard from "../cards/carousel/comedian";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import { Comedian } from "../../objects/class/comedian/Comedian";

interface TrendingComedianListProps {
    comedians: ComedianDTO[];
}
const TrendingComedianList = ({ comedians }: TrendingComedianListProps) => {
    return (
        <div className="bg-green-500 max-h-96 flex flex-col overflow-scroll  gap-10 p-4">
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

export default TrendingComedianList;
