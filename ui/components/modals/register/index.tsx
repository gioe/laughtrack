"use client";

import { useRouter } from "next/navigation";
import { useLoginModal, useRegisterModal } from "@/hooks/modalState";
import LaughtrackSignup from "@/ui/pages/register";
import FullScreenModal from "../fullscreen";

const RegisterModal = () => {
    const registerModal = useRegisterModal();
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
            <LaughtrackSignup handleLoginPick={showLoginPage} />
        </FullScreenModal>
    );
};

export default RegisterModal;
