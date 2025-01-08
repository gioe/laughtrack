"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { clearShowsFromClubSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import toast from "react-hot-toast";
import BaseForm from "..";
import ClearClubFormBody from "./body";

interface ClearShowsFormProps {
    name: string;
    onSubmit: () => void;
}

export default function ClearShowsFromClubForm({
    name,
    onSubmit,
}: ClearShowsFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof clearShowsFromClubSchema>>({
        resolver: zodResolver(clearShowsFromClubSchema),
        defaultValues: {
            clubName: name,
        },
    });

    const submitForm = async (
        data: z.infer<typeof clearShowsFromClubSchema>,
    ) => {
        try {
            setIsLoading(true);
            const response = await fetch(`/api/club/${data.clubName}/clear`, {
                method: "DELETE",
                headers: {
                    "Content-Type": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error("Failed to clear shows");
            }

            setIsLoading(false);
            toast.success("Successfully updated");
        } catch (error) {
            setIsLoading(false);
            toast.error(`Something went wrong: ${error}`);
        } finally {
            onSubmit();
        }
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<ClearClubFormBody />}
        />
    );
}
