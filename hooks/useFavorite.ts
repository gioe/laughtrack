'use client'
import { useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRegisterModal } from '@/hooks/modal';
import { makeRequest } from '@/util/actions/makeRequest';
import { APIRoutePath, RestAPIAction } from '@/objects/enum';

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
    const registerModal = useRegisterModal();
    const [isFavorite, setIsFavorite] = useState(initialState);

    const requireLogin = useCallback(() => {
        console.log(`OPEN MODAL`)
        registerModal.onOpen();
    }, [registerModal]);

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status === "authenticated") {
            // Optimistically update the UI
            const newFavoriteState = !isFavorite;

            setIsFavorite(newFavoriteState);

            try {
                const response = await makeRequest<boolean>(APIRoutePath.ComedianFavorite, {
                    method: RestAPIAction.PUT,
                    session: session.data,
                    body: {
                        comedianId: entityId,
                        setFavorite: newFavoriteState,
                    },
                });

                // If the response doesn't match our optimistic update, revert
                if (response !== newFavoriteState) {
                    setIsFavorite(!newFavoriteState);
                }
            } catch (error) {
                // Revert the optimistic update on error
                setIsFavorite(!newFavoriteState);
                console.error('Failed to update favorite status:', error);
                // Optionally add error notification here
            }
        } else {
            console.log('User must be logged in to favorite');
            requireLogin();
        }
    };

    return {
        isFavorite,
        handleFavoriteClick,
    };
};
