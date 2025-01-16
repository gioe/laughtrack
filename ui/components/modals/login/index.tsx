"use client";

import { useRouter } from "next/navigation";
import { useLoginModal, useRegisterModal } from "@/hooks/modalState";
import LaughtrackLogin from "@/ui/pages/login";
import FullScreenModal from "../fullscreen";

const LoginModal = () => {
    const router = useRouter();
    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();

    const onSubmit = () => {
        router.refresh();
        loginModal.onClose();
    };

    const showRegistrationPage = () => {
        loginModal.onClose();
        router.refresh();
        registerModal.onOpen();
    };

    return (
        <FullScreenModal
            isOpen={loginModal.isOpen}
            onClose={() => loginModal.onClose()}
        >
            <LaughtrackLogin handleRegisterClick={showRegistrationPage} />
        </FullScreenModal>
    );
};

export default LoginModal;
