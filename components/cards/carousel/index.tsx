"use client";

import {
    Card,
    CardHeader,
    CardBody,
    CardFooter,
} from "@material-tailwind/react";
import SocialMediaBar from "../../social/bar";
import LinkedImage from "../../image/link";
import { CarouselEntity } from "../../../objects/interface";

interface CarouselCardProps {
    entity: string;
}

const CarouselCard: React.FC<CarouselCardProps> = ({ entity }) => {
    const parsedEntity = JSON.parse(entity) as CarouselEntity;

    return (
        <Card className="flex flex-row bg-champagne cursor-pointer hover:scale-105 transform transition duration-300 ease-out w-72 h-48 lg:flex-col lg:h-72 lg:w-80">
            <CardHeader floated={false} className="h-1/2">
                <LinkedImage
                    priority
                    destination={`/${parsedEntity.type.valueOf()}/${parsedEntity.name}`}
                    imageUrl={parsedEntity.cardImageUrl}
                    alt={parsedEntity.type.valueOf()}
                />
            </CardHeader>
            <div className="bg-black h-1/4 w-full text-center">
                <CardBody>
                    <h2 className="bg-red-800">{parsedEntity.name}</h2>

                    {parsedEntity.showCount && (
                        <h2 className="bg-yellow-900">{`${parsedEntity.showCount ?? 0} upcoming shows`}</h2>
                    )}
                </CardBody>
            </div>
            <CardFooter>
                {parsedEntity.socialData && (
                    <div className="h-1/4 w-32">
                        <SocialMediaBar data={parsedEntity.socialData} />
                    </div>
                )}
            </CardFooter>
        </Card>
    );
};

export default CarouselCard;
