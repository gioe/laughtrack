"use client";

import { editComedianSchema } from "./schema";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import EditComedianFormBody from "./body";
import { useRouter } from "next/navigation";
import { Comedian } from "../../../../../../../../objects/class/comedian/Comedian";
import BaseForm from "../../../../../../../../components/form";

interface EditComedianFormProps {
    comedian: Comedian;
}

export default function EditComedianForm({ comedian }: EditComedianFormProps) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof editComedianSchema>>({
        resolver: zodResolver(editComedianSchema),
        defaultValues: {
            instagram: {
                account: comedian?.socialData?.instagram?.account ?? "",
                following:
                    comedian?.socialData?.instagram?.following.toString() ??
                    "0",
            },
            tiktok: {
                account: comedian?.socialData?.tiktok?.account ?? "",
                following:
                    comedian?.socialData?.tiktok?.following.toString() ?? "",
            },
            youtube: {
                account: comedian?.socialData?.youtube?.account ?? "",
                following:
                    comedian?.socialData?.youtube?.following.toString() ?? "",
            },
            linktree: comedian?.socialData?.linktree ?? "",
            website: comedian?.socialData?.website ?? "",
            cardImage: undefined,
            bannerImage: undefined,
            ids: comedian?.tagIds,
        },
    });

    const submitForm = (data: z.infer<typeof editComedianSchema>) => {
        setIsLoading(true);
        axios
            .put(`/api/comedian/${comedian.name}/admin`, {
                ...data,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                }
            })
            .finally(() => {
                router.refresh();
            });
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={
                <EditComedianFormBody
                    comedian={comedian}
                    form={form}
                    isLoading={isLoading}
                />
            }
        />
    );
}
