"use client";

import Modal from "..";
import { useRouter } from "next/navigation";
import AddComedianToShowForm from "../../form/modifyLineup";
import { useModifyLineupModal } from "../../../hooks/modalState";

interface ModifyLineupModalProps {
    identifier: string;
}

const ModifyLineupModal = ({ identifier }: ModifyLineupModalProps) => {
    const addComedianModal = useModifyLineupModal();
    const router = useRouter();

    const onClose = () => {
        router.refresh();
        addComedianModal.onClose();
    };

    return (
        <Modal
            isOpen={addComedianModal.isOpen}
            body={<AddComedianToShowForm id={identifier} onSubmit={onClose} />}
        />
    );
};

export default ModifyLineupModal;
