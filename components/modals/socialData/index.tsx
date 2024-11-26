"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import { useSocialDataModal } from "../../../hooks/modalState";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import EditSocialDataForm from "../../form/forms/socialData";

const EditSocialDataModal = () => {
    const comedian = JSON.parse(entityString) as Comedian;
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
            body={
                <EditSocialDataForm comedian={comedian} onSubmit={onSubmit} />
            }
        />
    );
};

export default EditSocialDataModal;
