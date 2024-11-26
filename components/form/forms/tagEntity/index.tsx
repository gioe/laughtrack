"use client";

import toast from "react-hot-toast";
import { tagEntitySchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import axios from "axios";
import { useState } from "react";
import { EntityType } from "../../../../objects/enum";
import BaseForm from "..";
import TagEntityFormBody from "./body";
import { FilterContainer } from "../../../../objects/class/tag/FilterContainer";

interface TagEntityFormProps {
    containers: FilterContainer[];
    onSubmit: () => void;
    entityId: number;
    type: EntityType;
}

export default function TagEntityForm({
    containers,
    entityId,
    type,
    onSubmit,
}: TagEntityFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof tagEntitySchema>>({
        resolver: zodResolver(tagEntitySchema),
        defaultValues: {
            entityId,
            tagIds: [],
        },
    });

    const submitForm = (data: z.infer<typeof tagEntitySchema>) => {
        setIsLoading(true);

        axios
            .post(`/api/${type.valueOf()}/${data.entityId}/tag`, {
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
            body={<TagEntityFormBody form={form} tagContainers={containers} />}
        />
    );
}
