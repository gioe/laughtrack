"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import useMergeComediansModal from "../../../../hooks/useMergeComediansModal";
import Modal from "../..";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Comedian } from "../../../../objects/classes/comedian/Comedian";
import MergeComediansForm from "./form";
import { mergeComediansSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

interface MergeComediansModalParams {
    comedianString: string;
}

const MergeComediansModal: React.FC<MergeComediansModalParams> = ({
    comedianString,
}) => {
    const comedian = JSON.parse(comedianString) as Comedian;
    const mergeComediansModal = useMergeComediansModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof mergeComediansSchema>>({
        resolver: zodResolver(mergeComediansSchema),
        defaultValues: {
            childComedianId: comedian.id,
            parentComedianId: comedian.id,
        },
    });

    const onSubmit = (data: z.infer<typeof mergeComediansSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/merge", {
                parentId: data.parentComedianId,
                childId: data.childComedianId,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    mergeComediansModal.onClose();
                }
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={mergeComediansModal.isOpen}
            title="Merge With Comedian"
            actionLabel="Continue"
            onClose={mergeComediansModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<MergeComediansForm isLoading={isLoading} form={form} />}
        />
    );
};

export default MergeComediansModal;
