"use client";

import { useForm } from "react-hook-form";
import { addComedianToShowSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import toast from "react-hot-toast";
import axios from "axios";
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

    const submitForm = (data: z.infer<typeof addComedianToShowSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/merge", {
                showId: data.showId,
                comedians: data.comedians,
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
            body={<ModifyLineupFormBody form={form} />}
        />
    );
}
