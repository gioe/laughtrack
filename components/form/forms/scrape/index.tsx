"use client";

import { scrapeClubSchema } from "./schema";
import axios from "axios";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import BaseForm from "..";
import ScrapeEntityFormBody from "./body";
import { useEntityTypeContext } from "../../../../contexts/EntityContext";

interface ScrapeEntityFormProps {
    entityId: number;
    onSubmit: () => void;
}

export default function ScrapeEntityForm({
    entityId,
    onSubmit,
}: ScrapeEntityFormProps) {
    const { currentEntityContext } = useEntityTypeContext();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof scrapeClubSchema>>({
        resolver: zodResolver(scrapeClubSchema),
        defaultValues: {
            entityId,
            headless: "true",
            pause: "false",
        },
    });

    const submitForm = (data: z.infer<typeof scrapeClubSchema>) => {
        setIsLoading(true);
        axios
            .post(`/api/${currentEntityContext?.valueOf()}/scrape`, {
                ids: [entityId],
                headless: data.headless,
                pause: data.pause,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setIsLoading(false);
                    toast.success(data.message);
                }
            })
            .catch((error: Error) => {
                setIsLoading(false);
                toast.error(`${error.message}`);
            })
            .finally(onSubmit);
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<ScrapeEntityFormBody form={form} type={type} />}
        />
    );
}
