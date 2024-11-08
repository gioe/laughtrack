"use client";

import { Entity } from "../../../objects/interfaces";
import CarouselCard from "../cards/CarouselCard";

interface EntityCarouselProps {
    entityString: string;
}

const EntityCarousel: React.FC<EntityCarouselProps> = ({ entityString }) => {
    const entities = JSON.parse(entityString) as Entity[];

    return (
        <div
            className="flex space-x-3 overflow-scroll
         scrollbar-hide p-3 -ml-3"
        >
            {entities.map((entity) => {
                return <CarouselCard key={entity.name} entity={entity} />;
            })}
        </div>
    );
};

export default EntityCarousel;
