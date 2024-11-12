"use client";

import {
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Typography,
} from "@material-tailwind/react";
import SocialMediaBar from "../social/SocialMediaBar";
import { Entity } from "../../objects/interfaces";
import LinkedImage from "../image/link";

interface CarouselCardProps {
    entity: Entity;
}

const CarouselCard: React.FC<CarouselCardProps> = ({ entity }) => {
    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <Card className="w-96">
                <CardHeader floated={false} className="h-80">
                    <LinkedImage
                        destination={`/${entity.type.valueOf()}/${entity.id}`}
                        imageUrl={entity.cardImageUrl}
                        alt={entity.type.valueOf()}
                    />
                </CardHeader>
                <CardBody className="text-center">
                    <Typography variant="h4" color="blue-gray" className="mb-2">
                        {entity.name}
                    </Typography>
                </CardBody>
                <CardFooter className="flex justify-center gap-7 pt-2">
                    {entity.socialData && (
                        <SocialMediaBar data={entity.socialData} />
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};

export default CarouselCard;
