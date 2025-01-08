"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import useAddNewComedianModal from "../../../hooks/modalState/useAddNewComedianModal";
import AddNewComedianForm from "../../form/addComedian";

const AddComedianModal = () => {
    const addNewComedianModal = useAddNewComedianModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        addNewComedianModal.onClose();
    };

    return (
        <Modal
            isOpen={addNewComedianModal.isOpen}
            body={<AddNewComedianForm onSubmit={onSubmit} />}
        />
    );
};

export default AddComedianModal;
