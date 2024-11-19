"use client";

import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { registerSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import axios from "axios";
import BaseForm from "..";
import { ButtonType } from "../../../../objects/enum";
import RegisterFormBody from "./body";

interface RegistrationFormProps {
    onSubmit: () => void;
}

export default function RegistrationForm({ onSubmit }: RegistrationFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof registerSchema>>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const submitForm = (data: z.infer<typeof registerSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/register", data)
            .then(() => {
                return signIn("credentials", {
                    ...data,
                    redirect: false,
                });
            })
            .then((callback) => {
                if (callback?.ok) {
                    toast.success("Logged in");
                }

                if (callback?.error) {
                    throw new Error(callback.error);
                }
            })
            .catch(() => toast.error("Something went wrong"))
            .finally(onSubmit);
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<RegisterFormBody form={form} isLoading={isLoading} />}
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "OK",
            }}
        />
    );
}
