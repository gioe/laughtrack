"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ClubInterface } from "../../../interfaces/club.interface";
import Modal from "./Modal";
import Heading from "../Heading";
import toast from "react-hot-toast";
import axios from "axios";
import useClearShowsModal from "../../../hooks/useClearShowsModal";

interface ClearShowsModalParams {
    club: ClubInterface;
}

const ClearShowsModal: React.FC<ClearShowsModalParams> = ({ club }) => {
    const clearShowsModal = useClearShowsModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = () => {
        setIsLoading(true);
        axios
            .post("/api/clear", {
                id: club.id,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    clearShowsModal.onClose();
                }
            });
    };

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <Heading title="Clear Shows" />
        </div>
    );

    return (
        <Modal
            disabled={isLoading}
            isOpen={clearShowsModal.isOpen}
            title="Clear"
            actionLabel="Continue"
            onClose={clearShowsModal.onClose}
            onSubmit={handleSubmit}
            body={bodyContent}
        />
    );
};

export default ClearShowsModal;
