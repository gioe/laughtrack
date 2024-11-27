"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import { useSocialDataModal } from "../../../hooks/modalState";
import EditSocialDataForm from "../../form/forms/socialData";

interface EditSocialDataModalProps {
    identifier: string;
}

const EditSocialDataModal = ({ identifier }: EditSocialDataModalProps) => {
    const socialDataModal = useSocialDataModal();
    const router = useRouter();

    const onSubmit = () => {
        socialDataModal.onClose();
        router.refresh();
    };

    return (
        <Modal
            isOpen={socialDataModal.isOpen}
            onClose={socialDataModal.onClose}
            body={<EditSocialDataForm name={identifier} onSubmit={onSubmit} />}
        />
    );
};

export default EditSocialDataModal;
