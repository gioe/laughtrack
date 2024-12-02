"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { addComedianFormSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import axios from "axios";
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

    const submitForm = (data: z.infer<typeof addComedianFormSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/comedian/add", {
                name: data.name,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                }
            })
            .finally(onSubmit);
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
