"use client";

import { useRouter } from "next/navigation";
import useRegisterModal from "../../../hooks/modalState/useRegisterModel";
import useLoginModal from "../../../hooks/modalState/useLoginModal";
import Modal from "..";
import RegistrationForm from "../../form/register";

const RegisterModal = () => {
    const registerModal = useRegisterModal();
    const loginModal = useLoginModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        registerModal.onClose();
    };

    const loginLinkClicked = () => {
        registerModal.onClose();
        loginModal.onOpen();
    };

    return (
        <Modal
            isOpen={registerModal.isOpen}
            body={
                <RegistrationForm
                    onSubmit={onSubmit}
                    onClose={registerModal.onClose}
                    handleLoginClick={loginLinkClicked}
                />
            }
        />
    );
};

export default RegisterModal;
