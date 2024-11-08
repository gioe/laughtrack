"use client";

import {
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Typography,
} from "@material-tailwind/react";
import { useState } from "react";
import SocialMediaBar from "../social/SocialMediaBar";
import Image from "next/image";
import { Entity } from "../../../objects/interfaces";

interface CarouselCardProps {
    entity: Entity;
}

const CarouselCard: React.FC<CarouselCardProps> = ({ entity }) => {
    const [src, setSrc] = useState<string>(entity.cardImageUrl);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <Card className="w-96">
                <CardHeader floated={false} className="h-80">
                    <div className="object-fill">
                        <Image
                            alt={entity.type.valueOf()}
                            src={src}
                            fill
                            onError={onError}
                            priority={false}
                            style={{ objectFit: "cover" }}
                        />
                    </div>
                </CardHeader>
                <CardBody className="text-center">
                    <Typography variant="h4" className="text-blue-gray-600">
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
