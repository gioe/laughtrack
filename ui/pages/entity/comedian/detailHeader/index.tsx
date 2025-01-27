"use client";

import React, { useCallback, useState } from "react";
import { Heart } from "lucide-react";
import ImageGrid from "@/ui/components/grid/image";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../socialColumn";
import { useFavoriteRegisterModal } from "@/hooks/modalState";
import { useSession } from "next-auth/react";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";

interface ClubDetailHeaderProps {
    comedian: ComedianDTO;
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    comedian,
}) => {
    const registerModal = useFavoriteRegisterModal();
    const parsedComedian = new Comedian(comedian);
    const session = useSession();

    const [, setIsOpen] = useState(false);
    const [isFavorite, setIsFavorite] = useState(parsedComedian.isFavorite);
    const [isLoading, setIsLoading] = useState(false);

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
        <div className="max-w-6xl mx-auto p-6">
            {/* Header Section */}
            <div className="flex justify-between items-start mb-6">
                <div className="flex items-center gap-2">
                    <h1 className="text-3xl font-bold text-gray-900">
                        {parsedComedian.name}
                    </h1>
                </div>

                <button
                    onClick={handleFavoriteClick}
                    disabled={isLoading}
                    className={`flex items-center gap-2 ${
                        isFavorite
                            ? "text-red-700 hover:text-red-800"
                            : "text-copper hover:text-copper"
                    } transition-colors duration-200 disabled:opacity-50`}
                >
                    <Heart
                        className={`w-4 h-4 ${isFavorite ? "fill-current" : ""}`}
                    />
                    <span className="text-copper">
                        {isFavorite
                            ? "Remove from Favorites"
                            : "Add to Favorites"}
                    </span>
                </button>
            </div>

            {/* Image Grid */}
            <ImageGrid
                images={[
                    {
                        url: comedian.imageUrl,
                        alt: comedian.name,
                    },
                ]}
            />
            <div className="pb-4">
                <SocialMediaColumn comedian={comedian} />
            </div>
        </div>
    );
};

export default ComedianDetailHeader;
