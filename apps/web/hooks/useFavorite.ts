"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { useSession } from "next-auth/react";
import useLoginModal from "./useLoginModal";
import { favorite } from "@/app/actions/favorite";
import { pendingFavorite } from "@/util/pendingFavorite";

interface UseFavoriteProps {
    initialState: boolean;
    entityId: string;
}

interface UseFavoriteReturn {
    isFavorite: boolean;
    handleFavoriteClick: (e: React.MouseEvent) => Promise<void>;
    isAuthenticated: boolean;
}

const FAVORITE_ERROR_MSG = "Failed to update favorite. Please try again.";
const SIGNIN_NUDGE_MSG = "Sign in to save your favorites";

export const useFavorite = ({
    initialState,
    entityId,
}: UseFavoriteProps): UseFavoriteReturn => {
    const session = useSession();
    const loginModal = useLoginModal();
    const [isFavorite, setIsFavorite] = useState(initialState);
    const pendingConsumedRef = useRef(false);

    const requireLogin = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const performFavorite = useCallback(
        async (newFavoriteState: boolean) => {
            setIsFavorite(newFavoriteState);

            try {
                const response = await favorite(newFavoriteState, entityId);
                if (
                    response !== null &&
                    typeof response === "object" &&
                    "error" in response &&
                    typeof response.error === "string"
                ) {
                    setIsFavorite(!newFavoriteState);
                    toast.error(response.error);
                } else if (response === undefined) {
                    console.warn(
                        "[useFavorite] server action returned undefined — possible server-session mismatch",
                    );
                    setIsFavorite(!newFavoriteState);
                    toast.error(FAVORITE_ERROR_MSG);
                } else if (response !== newFavoriteState) {
                    setIsFavorite(!newFavoriteState);
                    toast.error(FAVORITE_ERROR_MSG);
                }
            } catch {
                setIsFavorite(!newFavoriteState);
                toast.error(FAVORITE_ERROR_MSG);
            }
        },
        [entityId],
    );

    // Once authenticated, complete any favorite action the user started while logged out.
    useEffect(() => {
        if (session.status !== "authenticated") return;
        if (pendingConsumedRef.current) return;
        const pending = pendingFavorite.consume(entityId);
        if (!pending) return;
        pendingConsumedRef.current = true;
        void performFavorite(pending.setFavorite);
    }, [session.status, entityId, performFavorite]);

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status === "authenticated") {
            await performFavorite(!isFavorite);
        } else {
            pendingFavorite.set({
                entityId,
                setFavorite: !isFavorite,
            });
            toast(SIGNIN_NUDGE_MSG, { icon: "❤️" });
            requireLogin();
        }
    };

    return {
        isFavorite,
        handleFavoriteClick,
        isAuthenticated: session.status === "authenticated",
    };
};
