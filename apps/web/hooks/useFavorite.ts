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

    const FAVORITE_ERROR_MSG = "Failed to update favorite. Please try again.";

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
                    "error" in response &&
                    typeof response.error === "string"
                ) {
                    // FavoriteError: surface the descriptive message from validation/server
                    setIsFavorite(!newFavoriteState);
                    toast.error(response.error);
                } else if (response === undefined) {
                    // Server-side auth guard fired despite authenticated client
                    console.warn(
                        "[useFavorite] server action returned undefined — possible server-session mismatch",
                    );
                    setIsFavorite(!newFavoriteState);
                    toast.error(FAVORITE_ERROR_MSG);
                } else if (response !== newFavoriteState) {
                    // Unexpected boolean mismatch — revert with generic message
                    setIsFavorite(!newFavoriteState);
                    toast.error(FAVORITE_ERROR_MSG);
                }
            } catch {
                // Revert the optimistic update on error
                setIsFavorite(!newFavoriteState);
                toast.error(FAVORITE_ERROR_MSG);
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
