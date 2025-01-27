"use client";

import { useRouter } from "next/navigation";
import {
    useFavoriteRegisterModal,
    useLoginModal,
    useRegisterModal,
} from "@/hooks/modalState";
import LaughtrackSignup from "@/ui/pages/register";
import FullScreenModal from "../fullscreen";

const FavoriteRegisterModal = () => {
    const registerModal = useFavoriteRegisterModal();
    const loginModal = useLoginModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        registerModal.onClose();
    };

    const showLoginPage = () => {
        registerModal.onClose();
        loginModal.onOpen();
    };

    return (
        <FullScreenModal
            isOpen={registerModal.isOpen}
            onClose={() => registerModal.onClose()}
        >
            <LaughtrackSignup
                handleLoginPick={showLoginPage}
                handleSubmit={onSubmit}
                subtitle="Create an account to save Favorites"
            />
        </FullScreenModal>
    );
};

export default FavoriteRegisterModal;
