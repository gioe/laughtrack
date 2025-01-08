"use client";

import { useRouter } from "next/navigation";
import { useClearShowsModal } from "../../../hooks/modalState";
import Modal from "..";
import ClearShowsFromClubForm from "../../form/clearClub";

interface ClearShowModalProps {
    identifier: string;
}

const ClearShowsModal = ({ identifier }: ClearShowModalProps) => {
    const clearShowsModal = useClearShowsModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        clearShowsModal.onClose();
    };

    return (
        <Modal
            isOpen={clearShowsModal.isOpen}
            body={
                <ClearShowsFromClubForm name={identifier} onSubmit={onSubmit} />
            }
        />
    );
};

export default ClearShowsModal;
