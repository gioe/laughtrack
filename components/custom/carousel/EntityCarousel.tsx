"use client";

import { SocialDiscoverable } from "../../../interfaces";
import { ImageRepresentable } from "../../../interfaces/imageRepresentable.interface";
import EntityType from "../icons/MiniEntityIcon";
import BasicEntityInfoCard from "../tables/cards/BasicEntityInfoCard";

interface EntityCarouselProps {
    type: EntityType;
    entities: (ImageRepresentable & SocialDiscoverable)[];
}

const EntityCarousel: React.FC<EntityCarouselProps> = ({ entities, type }) => {
    return (
        <div
            className="flex space-x-3 overflow-scroll
         scrollbar-hide p-3 -ml-3"
        >
            {entities.map((entity) => {
                return (
                    <BasicEntityInfoCard
                        key={entity.name}
                        type={type}
                        entity={entity}
                    />
                );
            })}
        </div>
    );
};

export default EntityCarousel;
