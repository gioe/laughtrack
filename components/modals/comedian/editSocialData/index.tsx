"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import Modal from "../..";
import { z } from "zod";
import toast from "react-hot-toast";
import axios from "axios";
import EditSocialDataForm from "./form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSocialDataModal } from "../../../../hooks";
import { Comedian } from "../../../../objects/classes/comedian/Comedian";
import { editSocialDataSchema } from "./form/schema";

interface EditSocialDataModalProps {
    comedianString: string;
}

const EditSocialDataModal: React.FC<EditSocialDataModalProps> = ({
    comedianString,
}) => {
    const comedian = JSON.parse(comedianString) as Comedian;
    const socialDataModal = useSocialDataModal();
    const router = useRouter();

    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof editSocialDataSchema>>({
        resolver: zodResolver(editSocialDataSchema),
        defaultValues: {
            instagram: {
                account: comedian?.socialData?.instagram?.account ?? "",
                following: comedian?.socialData?.instagram?.following ?? 0,
            },
            tikTok: {
                account: comedian?.socialData?.tiktok?.account ?? "",
                following: comedian?.socialData?.tiktok?.following ?? 0,
            },
            facebook: {
                account: comedian?.socialData?.facebook?.account ?? "",
                following: comedian?.socialData?.facebook?.following ?? 0,
            },
            twitter: {
                account: comedian?.socialData?.twitter?.account ?? "",
                following: comedian?.socialData?.twitter?.following ?? 0,
            },
            youtube: {
                account: comedian?.socialData?.youtube?.account ?? "",
                following: comedian?.socialData?.youtube?.following ?? 0,
            },
            website: comedian?.socialData?.website ?? "",
            cardImage: undefined,
            bannerImage: undefined,
        },
    });

    const onSubmit = (data: z.infer<typeof editSocialDataSchema>) => {
        setIsLoading(true);
        // axios
        //     .post("/api/editSocial", {
        //         ...data,
        //         id: comedian?.id,
        //     })
        //     .then((response) => {
        //         if (response) {
        //             setIsLoading(false);
        //             toast.success("Successfully updated");
        //             router.refresh();
        //             socialDataModal.onClose();
        //         }
        //     });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={socialDataModal.isOpen}
            title="Edit Social Data"
            actionLabel="Continue"
            onClose={socialDataModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<EditSocialDataForm isLoading={isLoading} form={form} />}
        />
    );
};

export default EditSocialDataModal;
