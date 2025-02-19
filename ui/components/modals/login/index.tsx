"use client";

import { useRouter } from "next/navigation";
import LaughtrackLogin from "@/ui/pages/login";
import FullScreenModal from "../fullscreen";
import { useLoginModal } from "@/hooks";

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
            <LaughtrackLogin handleSubmit={onSubmit} />
        </FullScreenModal>
    );
};

export default LoginModal;
