"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import TagEntityForm from "../../form/forms/tagEntity";
import useAddEntityTagModal from "../../../hooks/modalState/useAddEntityTagModal";
import { useDataProvider } from "../../../contexts/EntityDataContext";

const TagEntityModal = () => {
    const { filters } = useDataProvider();

    const router = useRouter();
    const addEntityTagModal = useAddEntityTagModal();

    const onSubmit = () => {
        router.refresh();
        addEntityTagModal.onClose();
    };

    return (
        <Modal
            isOpen={addEntityTagModal.isOpen}
            onClose={addEntityTagModal.onClose}
            body={
                <TagEntityForm
                    filters={filters}
                    entityId={entityId}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default TagEntityModal;
