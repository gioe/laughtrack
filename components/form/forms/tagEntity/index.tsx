"use client";

import toast from "react-hot-toast";
import { tagEntitySchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import axios from "axios";
import { useState } from "react";
import BaseForm from "..";
import TagEntityFormBody from "./body";
import { usePageContext } from "../../../../contexts/PageEntityProvider";

interface TagEntityFormProps {
    name: string;
    onSubmit: () => void;
}

export default function TagEntityForm({ name, onSubmit }: TagEntityFormProps) {
    const { primaryEntity } = usePageContext();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof tagEntitySchema>>({
        resolver: zodResolver(tagEntitySchema),
        defaultValues: {
            entityName: name,
            tagIds: [],
        },
    });

    const submitForm = (data: z.infer<typeof tagEntitySchema>) => {
        setIsLoading(true);

        axios
            .post(`/api/${primaryEntity?.valueOf()}/${data.entityName}/tag`, {
                tags: data.tagIds,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                }
            })
            .finally(onSubmit);
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<TagEntityFormBody form={form} />}
        />
    );
}
