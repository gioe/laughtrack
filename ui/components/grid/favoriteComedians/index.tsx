"use client";

import { useEffect, useState } from "react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import ComedianHeadshot from "@/ui/components/image/comedian";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath } from "@/objects/enum";
import { Loader2 } from "lucide-react";

interface FavoriteComediansGridProps {
    userId: string;
}

interface FavoritesResponse {
    comedians: ComedianDTO[];
}

export default function FavoriteComediansGrid({
    userId,
}: FavoriteComediansGridProps) {
    const [comedians, setComedians] = useState<ComedianDTO[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchFavorites = async () => {
            try {
                const response = await makeRequest<FavoritesResponse>(
                    APIRoutePath.Favorites,
                    {
                        searchParams: new URLSearchParams({ userId }),
                    },
                );
                setComedians(response.comedians);
            } catch (error) {
                console.error("Failed to fetch favorite comedians:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchFavorites();
    }, [userId]);

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 text-copper animate-spin" />
            </div>
        );
    }

    if (comedians.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">
                    You haven't favorited any comedians yet.
                </p>
                <p className="text-gray-400 text-sm mt-2">
                    Browse comedians and click the heart icon to add them to
                    your favorites.
                </p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {comedians.map((comedian) => (
                <ComedianHeadshot
                    key={comedian.uuid}
                    comedian={new Comedian(comedian)}
                    variant="grid"
                />
            ))}
        </div>
    );
}
