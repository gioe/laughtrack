"use client";

import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { editSocialDataSchema } from "./schema";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import BaseForm from "..";
import EditSocialDataFormBody from "./body";

interface EditSocialDataInterfaceProps {
    onSubmit: () => void;
    comedian: Comedian;
}

export default function EditSocialDataForm({
    onSubmit,
    comedian,
}: EditSocialDataInterfaceProps) {
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

    const submitForm = (data: z.infer<typeof editSocialDataSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/editSocial", {
                ...data,
                id: comedian?.id,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                }
            })
            .finally(() => {
                onSubmit();
            });
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<EditSocialDataFormBody form={form} isLoading={isLoading} />}
        />
    );
}
