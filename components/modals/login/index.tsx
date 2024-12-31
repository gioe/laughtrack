"use client";

import { useRouter } from "next/navigation";
import useLoginModal from "../../../hooks/modalState/useLoginModal";
import Modal from "..";
import LoginForm from "../../form/login";

const LoginModal = () => {
    const router = useRouter();
    const loginModal = useLoginModal();

    const onSubmit = () => {
        router.refresh();
        loginModal.onClose();
    };

    return (
        <Modal
            isOpen={loginModal.isOpen}
            body={
                <LoginForm onSubmit={onSubmit} onClose={loginModal.onClose} />
            }
        />
    );
};

export default LoginModal;
