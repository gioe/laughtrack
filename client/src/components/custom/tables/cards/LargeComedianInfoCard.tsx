'use client';

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { LineupItem } from "@/interfaces/lineupItem.interface";
import {
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Typography
} from "@material-tailwind/react";
import { useState } from "react";
import SocialMediaBar from "../../social/SocialMediaBar";
import Image from "next/image";

interface LargeComedianInfoCardProps {
    comedian: ComedianInterface | LineupItem
}

const LargeComedianInfoCard: React.FC<LargeComedianInfoCardProps> = ({
    comedian,
}) => {

    const [src, setSrc] = useState<string>(`/images/comedians/square/${comedian.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };


    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <Card className="w-96">
                <CardHeader floated={false} className="h-80">
                    <div className="object-fill">
                        <Image alt="Comedian"
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
                        {comedian.name}
                    </Typography>
                </CardBody>
                <CardFooter className="flex justify-center gap-7 pt-2">
                    <SocialMediaBar data={comedian.socialData} />
                </CardFooter>
            </Card>
        </div>
    );
}

export default LargeComedianInfoCard;