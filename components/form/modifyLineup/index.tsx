"use client";

import { useForm } from "react-hook-form";
import { addComedianToShowSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import toast from "react-hot-toast";
import BaseForm from "..";
import ModifyLineupFormBody from "./body";

interface AddComedianToShowFormProps {
    id: string;
    onSubmit: () => void;
}

export default function AddComedianToShowForm({
    id,
    onSubmit,
}: AddComedianToShowFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof addComedianToShowSchema>>({
        resolver: zodResolver(addComedianToShowSchema),
        defaultValues: {
            showId: Number(id),
            comedians: [],
        },
    });

    const submitForm = async (
        data: z.infer<typeof addComedianToShowSchema>,
    ) => {
        try {
            setIsLoading(true);
            const response = await fetch("/api/merge", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    showId: data.showId,
                    comedians: data.comedians,
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to add comedian to show");
            }

            setIsLoading(false);
            toast.success("Successfully updated");
        } catch (error) {
            // Handle error appropriately
            console.error("Error adding comedian to show:", error);
        } finally {
            onSubmit();
        }
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<ModifyLineupFormBody form={form} />}
        />
    );
}
