"use client";
import { useState, useCallback } from "react";
import toast from "react-hot-toast";
import { useSession } from "next-auth/react";
import useLoginModal from "./useLoginModal";
import { favorite } from "@/app/actions/favorite";

interface UseFavoriteProps {
    initialState: boolean;
    entityId: string;
}

interface UseFavoriteReturn {
    isFavorite: boolean;
    handleFavoriteClick: (e: React.MouseEvent) => Promise<void>;
}

export const useFavorite = ({
    initialState,
    entityId,
}: UseFavoriteProps): UseFavoriteReturn => {
    const session = useSession();
    const loginModal = useLoginModal();
    const [isFavorite, setIsFavorite] = useState(initialState);

    const requireLogin = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status === "authenticated") {
            // Optimistically update the UI
            const newFavoriteState = !isFavorite;

            setIsFavorite(newFavoriteState);

            try {
                const response = await favorite(newFavoriteState, entityId);
                if (
                    response !== null &&
                    typeof response === "object" &&
                    "error" in response
                ) {
                    // FavoriteError: surface the descriptive message from validation/server
                    setIsFavorite(!newFavoriteState);
                    toast.error(response.error);
                } else if (response !== newFavoriteState) {
                    // Unexpected boolean mismatch or undefined — revert with generic message
                    setIsFavorite(!newFavoriteState);
                    toast.error("Failed to update favorite. Please try again.");
                }
            } catch {
                // Revert the optimistic update on error
                setIsFavorite(!newFavoriteState);
                toast.error("Failed to update favorite. Please try again.");
            }
        } else {
            requireLogin();
        }
    };

    return {
        isFavorite,
        handleFavoriteClick,
    };
};
