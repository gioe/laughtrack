"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import axios from "axios";
import { z } from "zod";
import { clearShowsFromClubSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import ClearShowsFromClubForm from "./form";
import { useClearShowsModal } from "../../../../hooks";
import Modal from "../..";

interface ClearShowsModalParams {
    clubId: number;
}

const ClearShowsModal: React.FC<ClearShowsModalParams> = ({ clubId }) => {
    const clearShowsModal = useClearShowsModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof clearShowsFromClubSchema>>({
        resolver: zodResolver(clearShowsFromClubSchema),
        defaultValues: {
            clubId,
        },
    });

    const onSubmit = (data: z.infer<typeof clearShowsFromClubSchema>) => {
        setIsLoading(true);
        axios
            .put(`/api/club/${data.clubId}/clear`)
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    clearShowsModal.onClose();
                }
            })
            .catch((error: Error) => {
                setIsLoading(false);
                toast.error(`Something went wrong: ${error}`);
                clearShowsModal.onClose();
            })
            .finally(() => {
                router.refresh();
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={clearShowsModal.isOpen}
            title="Clear"
            actionLabel="Continue"
            onClose={clearShowsModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<ClearShowsFromClubForm />}
        />
    );
};

export default ClearShowsModal;
