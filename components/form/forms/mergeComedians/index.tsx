"use client";

import { FormInput } from "../../components/input";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { mergeComediansSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import Heading from "../../../modals/heading";
import BaseForm from "..";

interface MergeComediansFormProps {
    comedian: Comedian;
    onSubmit: () => void;
}

export default function MergeComediansForm({
    comedian,
    onSubmit,
}: MergeComediansFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof mergeComediansSchema>>({
        resolver: zodResolver(mergeComediansSchema),
        defaultValues: {
            childComedianId: comedian.id,
            parentComedianId: comedian.id,
        },
    });

    const submitForm = (data: z.infer<typeof mergeComediansSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/merge", {
                parentId: data.parentComedianId,
                childId: data.childComedianId,
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
                    <Heading
                        title="Merge Comedians"
                        subtitle="Merge comedian with a parent entity"
                    />
                    <FormInput
                        type={"number"}
                        isLoading={isLoading}
                        name="parentId"
                        placeholder="Parent Id"
                        form={form}
                    />
                </div>
            }
        />
    );
}
