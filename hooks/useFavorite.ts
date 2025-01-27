import { useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useFavoriteRegisterModal } from '@/hooks/modalState';
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
    const registerModal = useFavoriteRegisterModal();
    const [isFavorite, setIsFavorite] = useState(initialState);

    const requireLogin = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    const handleFavoriteClick = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (session.status === "authenticated") {
            await makeRequest(APIRoutePath.ComedianFavorite, {
                method: RestAPIAction.POST,
                body: {
                    comedianId: entityId,
                    isFavorite,
                },
            }).then((data: { state: boolean }) => {
                setIsFavorite(data.state);
            });
        } else {
            requireLogin();
        }
    };

    return {
        isFavorite,
        handleFavoriteClick,
    };
};
