"use client";

import { useRouter } from "next/navigation";
import useRegisterModal from "../../../hooks/modalState/useRegisterModel";
import useLoginModal from "../../../hooks/modalState/useLoginModal";
import Modal from "..";
import RegistrationForm from "../../form/forms/register";
import RegistrationFormFooter from "../../form/forms/register/footer";

const RegisterModal = () => {
    const registerModal = useRegisterModal();
    const loginModal = useLoginModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        registerModal.onClose();
    };

    const handleLoginClick = () => {
        registerModal.onClose();
        loginModal.onOpen();
    };

    return (
        <Modal
            isOpen={registerModal.isOpen}
            onClose={registerModal.onClose}
            body={<RegistrationForm onSubmit={onSubmit} />}
            footer={
                <RegistrationFormFooter handleLoginClick={handleLoginClick} />
            }
        />
    );
};

export default RegisterModal;
