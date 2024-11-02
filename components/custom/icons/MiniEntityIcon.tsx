"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { ImageRepresentable } from "../../../interfaces/imageRepresentable.interface";
import { EntityType } from "../../../util/enum";

interface MiniComedianIconProps {
    type: EntityType;
    entity: ImageRepresentable;
}

export const MiniEntityIcon: React.FC<MiniComedianIconProps> = ({
    entity,
    type,
}) => {
    const [src, setSrc] = useState<string>(
        `/images/${type.valueOf()}/square/${entity.name}.png`,
    );

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    return (
        <div className="flex flex-col w-20">
            <Link href={`/${type.valueOf()}/${entity.name}`}>
                <div
                    className="cursor-pointer hover:scale-105 t
            ransform transition duration-300 ease-out text-center"
                >
                    <div className="relative h-20 w-20">
                        <Image
                            alt="Comedian"
                            src={src}
                            fill
                            priority={false}
                            style={{ objectFit: "cover" }}
                            className="rounded-2xl"
                            onError={onError}
                        ></Image>
                    </div>

                    <div>
                        <p className="mt-1 md:text-sm text-xs text-black text-center">
                            {entity.name}
                        </p>
                    </div>
                </div>
            </Link>
        </div>
    );
};

export default EntityType;
