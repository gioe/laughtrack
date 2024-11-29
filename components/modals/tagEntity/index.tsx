"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import TagEntityForm from "../../form/forms/tagEntity";
import useAddEntityTagModal from "../../../hooks/modalState/useAddEntityTagModal";

interface TagEntityModalProps {
    identifier: string;
}

const TagEntityModal = ({ identifier }: TagEntityModalProps) => {
    const addEntityTagModal = useAddEntityTagModal();

    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        addEntityTagModal.onClose();
    };

    return (
        <Modal
            isOpen={addEntityTagModal.isOpen}
            onClose={addEntityTagModal.onClose}
            body={<TagEntityForm name={identifier} onSubmit={onSubmit} />}
        />
    );
};

export default TagEntityModal;
