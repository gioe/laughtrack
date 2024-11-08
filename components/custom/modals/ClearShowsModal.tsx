"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Modal from "./Modal";
import Heading from "../Heading";
import toast from "react-hot-toast";
import axios from "axios";
import useClearShowsModal from "../../../hooks/useClearShowsModal";
import { Club } from "../../../objects/classes/club/Club";

interface ClearShowsModalParams {
    clubString: string;
}

const ClearShowsModal: React.FC<ClearShowsModalParams> = ({ clubString }) => {
    const club = JSON.parse(clubString) as Club;

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
            form={}
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
