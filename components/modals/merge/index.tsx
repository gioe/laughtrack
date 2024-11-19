"use client";

import useMergeComediansModal from "../../../hooks/modalState/useMergeComediansModal";
import Modal from "..";
import { useRouter } from "next/navigation";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import MergeComediansForm from "../../form/forms/mergeComedians";

interface MergeComediansModalParams {
    entityString: string;
}

const MergeComediansModal: React.FC<MergeComediansModalParams> = ({
    entityString,
}) => {
    const comedian = JSON.parse(entityString) as Comedian;
    const mergeComediansModal = useMergeComediansModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        mergeComediansModal.onClose();
    };

    return (
        <Modal
            isOpen={mergeComediansModal.isOpen}
            onClose={mergeComediansModal.onClose}
            body={
                <MergeComediansForm comedian={comedian} onSubmit={onSubmit} />
            }
        />
    );
};

export default MergeComediansModal;
