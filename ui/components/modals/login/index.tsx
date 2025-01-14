"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import LoginForm from "../../form/login";
import { useLoginModal } from "@/hooks/modalState";
import LaughtrackLogin from "@/ui/pages/login";
import FullScreenModal from "../fullscreen";

const LoginModal = () => {
    const router = useRouter();
    const loginModal = useLoginModal();

    const onSubmit = () => {
        router.refresh();
        loginModal.onClose();
    };

    return (
        <FullScreenModal
            isOpen={loginModal.isOpen}
            onClose={() => loginModal.onClose()}
        >
            <LaughtrackLogin />
        </FullScreenModal>
    );
};

export default LoginModal;
