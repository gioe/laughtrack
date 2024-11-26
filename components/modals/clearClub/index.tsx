"use client";

import { useRouter } from "next/navigation";
import { useClearShowsModal } from "../../../hooks/modalState";
import Modal from "..";
import ClearShowsFromClubForm from "../../form/forms/clearClub";

const ClearShowsModal = () => {
    const clearShowsModal = useClearShowsModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        clearShowsModal.onClose();
    };

    return (
        <Modal
            isOpen={clearShowsModal.isOpen}
            onClose={clearShowsModal.onClose}
            body={
                <ClearShowsFromClubForm clubId={clubId} onSubmit={onSubmit} />
            }
        />
    );
};

export default ClearShowsModal;
