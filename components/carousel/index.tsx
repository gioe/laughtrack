"use client";

import { Entity } from "../../objects/interface";
import CarouselCard from "../cards/CarouselCard";

interface EntityCarouselProps {
    entities: string;
}

const EntityCarousel: React.FC<EntityCarouselProps> = ({ entities }) => {
    const entityObjects = JSON.parse(entities) as Entity[];

    return (
        <div
            className="flex space-x-3 overflow-scroll
         scrollbar-hide p-3 -ml-3"
        >
            {entityObjects.map((entity) => {
                return <CarouselCard key={entity.name} entity={entity} />;
            })}
        </div>
    );
};

export default EntityCarousel;
