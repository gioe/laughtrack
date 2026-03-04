'use client'
import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useSession } from 'next-auth/react';
import useLoginModal from './useLoginModal';
import { favorite } from '@/app/actions/favorite';

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
    entityId
}: UseFavoriteProps): UseFavoriteReturn => {
    const session = useSession();
    const loginModal = useLoginModal();
    const [isFavorite, setIsFavorite] = useState(initialState);

    const requireLogin = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const FAVORITE_ERROR_MSG = 'Failed to update favorite. Please try again.';

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status === "authenticated") {
            // Optimistically update the UI
            const newFavoriteState = !isFavorite;

            setIsFavorite(newFavoriteState);

            try {
                const response = await favorite(newFavoriteState, entityId);
                // If the response doesn't match our optimistic update, revert
                if (response !== newFavoriteState) {
                    setIsFavorite(!newFavoriteState);
                    toast.error(FAVORITE_ERROR_MSG);
                }
            } catch (error) {
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
