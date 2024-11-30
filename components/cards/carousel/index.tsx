"use client";

import {
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Typography,
} from "@material-tailwind/react";
import SocialMediaBar from "../../social/SocialMediaBar";
import LinkedImage from "../../image/link";
import { CarouselEntity } from "../../../objects/interface";

interface CarouselCardProps {
    entity: string;
}

const CarouselCard: React.FC<CarouselCardProps> = ({ entity }) => {
    const parsedEntity = JSON.parse(entity) as CarouselEntity;

    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <Card className="w-96">
                <CardHeader floated={false} className="h-80">
                    <LinkedImage
                        priority
                        destination={`/${parsedEntity.type.valueOf()}/${parsedEntity.name}`}
                        imageUrl={parsedEntity.cardImageUrl}
                        alt={parsedEntity.type.valueOf()}
                    />
                </CardHeader>
                <CardBody className="text-center">
                    <Typography variant="h4" color="blue-gray" className="mb-2">
                        {parsedEntity.name}
                    </Typography>
                    {parsedEntity.showCount && (
                        <Typography
                            color="blue-gray"
                            className="font-medium"
                            textGradient
                        >
                            {`${parsedEntity.showCount ?? 0} upcoming shows`}
                        </Typography>
                    )}
                </CardBody>
                <CardFooter className="flex justify-center gap-7 pt-2">
                    {parsedEntity.socialData && (
                        <SocialMediaBar data={parsedEntity.socialData} />
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};

export default CarouselCard;
