"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { addComedianFormSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import toast from "react-hot-toast";
import BaseForm from "..";
import AddNewComedianFormBody from "./body";

interface AddNewComedianFormProps {
    onSubmit: () => void;
}

export default function AddNewComedianForm({
    onSubmit,
}: AddNewComedianFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const submitForm = async (data: z.infer<typeof addComedianFormSchema>) => {
        try {
            setIsLoading(true);
            const response = await fetch("/api/comedian/add", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    name: data.name,
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to add comedian");
            }

            setIsLoading(false);
            toast.success("Successfully updated");
        } catch (error) {
            // Handle error appropriately
            console.error("Error adding comedian:", error);
        } finally {
            onSubmit();
        }
    };

    const form = useForm<z.infer<typeof addComedianFormSchema>>({
        resolver: zodResolver(addComedianFormSchema),
        defaultValues: {
            name: "",
        },
    });

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<AddNewComedianFormBody form={form} isLoading={isLoading} />}
        />
    );
}
