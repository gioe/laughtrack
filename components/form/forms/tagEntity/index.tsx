"use client";

import { TagInterface } from "../../../../objects/interface";
import { CheckboxFormComponent } from "../../components/checkbox";
import toast from "react-hot-toast";
import { tagEntitySchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import axios from "axios";
import { useState } from "react";
import { ButtonType, EntityType } from "../../../../objects/enum";
import BaseForm from "..";

interface TagEntityFormProps {
    tags: TagInterface[];
    onSubmit: () => void;
    entityId: number;
    type: EntityType;
}

export default function TagEntityForm({
    tags,
    entityId,
    type,
    onSubmit,
}: TagEntityFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const items = tags.map((tag: TagInterface) => {
        return {
            id: tag.id.toString(),
            name: tag.name,
        };
    });

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
            body={
                <div className="flex flex-col gap-4">
                    <CheckboxFormComponent
                        items={items}
                        form={form}
                        name={"tagIds"}
                    />
                </div>
            }
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "OK",
            }}
        />
    );
}
