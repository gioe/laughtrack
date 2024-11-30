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
import { usePageContext } from "../../../../contexts/PageEntityProvider";

interface ScrapeEntityFormProps {
    identifier: string;
    onSubmit: () => void;
}

export default function ScrapeEntityForm({
    identifier,
    onSubmit,
}: ScrapeEntityFormProps) {
    const { primaryEntity } = usePageContext();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof scrapeClubSchema>>({
        resolver: zodResolver(scrapeClubSchema),
        defaultValues: {
            entityIdentifier: identifier.toString(),
            headless: "true",
            pause: "false",
        },
    });

    const submitForm = (data: z.infer<typeof scrapeClubSchema>) => {
        setIsLoading(true);
        axios
            .post(`/api/${primaryEntity?.valueOf()}/scrape`, {
                ids: [identifier],
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
            body={<ScrapeEntityFormBody form={form} />}
        />
    );
}
