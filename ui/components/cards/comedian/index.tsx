"use client";

import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
import { useFavoriteRegisterModal } from "@/hooks/modalState";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import SocialMediaBar from "../../social/bar";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianLineupImage from "../../image/comedian/lineup";

interface ComedianGridCardProps {
    entity: string;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({ entity }) => {
    const registerModal = useFavoriteRegisterModal();
    const session = useSession();
    const comedian = new Comedian(JSON.parse(entity) as ComedianDTO);

    const [, setIsOpen] = useState(false);
    const [isFavorite, setIsFavorite] = useState(
        comedian.isFavorite ? true : false,
    );

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status == "authenticated") {
            await makeRequest(APIRoutePath.ComedianFavorite, {
                method: RestAPIAction.POST,
                body: {
                    comedianId: comedian.uuid,
                    isFavorite,
                },
            }).then((data: { state: boolean }) => {
                setIsFavorite(data.state);
            });
        } else {
            requireLogin();
        }
    };

    const requireLogin = useCallback(() => {
        setIsOpen((value) => !value);
        registerModal.onOpen();
    }, [registerModal]);

    return (
        <div className="bg-ivory rounded-xl overflow-hidden pb-4 px-4">
            <ComedianLineupImage
                comedian={comedian}
                handleFavoriteClick={handleFavoriteClick}
                sizes="(max-width: 768px) 100vw,
               (max-width: 1200px) 50vw,
               25vw"
            />

            <div className="mt-4">
                <h2 className="text-[22px] font-bold mb-1 font-outfit text-center">
                    {comedian.name}
                </h2>

                <p className="text-[18px] text-gray-600 mb-4 text-center font-dmSans">
                    {`${comedian.showCount ?? 0} upcoming shows`}
                </p>

                <div className="w-full">
                    {comedian.socialData && (
                        <SocialMediaBar data={comedian.socialData} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default ComedianGridCard;
