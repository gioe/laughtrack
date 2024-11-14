"use client";

import Modal from "..";
import { useRouter } from "next/navigation";
import { Show } from "../../../objects/class/show/Show";
import AddComedianToShowForm from "../../form/forms/modifyLineup";
import { useModifyLineupModal } from "../../../hooks";

interface ModifyLineupModalProps {
    entityString: string;
}

const ModifyLineupModal: React.FC<ModifyLineupModalProps> = ({
    entityString,
}) => {
    const show = JSON.parse(entityString) as Show;
    const addComedianModal = useModifyLineupModal();
    const router = useRouter();

    const onClose = () => {
        router.refresh();
        addComedianModal.onClose();
    };

    return (
        <Modal
            isOpen={addComedianModal.isOpen}
            onClose={onClose}
            body={<AddComedianToShowForm show={show} onSubmit={onClose} />}
        />
    );
};

export default ModifyLineupModal;
