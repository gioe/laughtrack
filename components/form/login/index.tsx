/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { loginSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import BaseForm from "..";
import LoginFormBody from "./body";

interface LoginFormProps {
    onSubmit: () => void;
}
export default function LoginForm({ onSubmit }: LoginFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof loginSchema>>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const submitForm = (data: z.infer<typeof loginSchema>) => {
        setIsLoading(true);

        signIn("credentials", {
            ...data,
            redirect: false,
        })
            .then((callback: any) => {
                setIsLoading(false);
                if (callback?.ok) {
                    toast.success("Logged in");
                }

                if (callback?.error) {
                    toast.error(callback.error);
                }
            })
            .finally(onSubmit);
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={<LoginFormBody form={form} isLoading={isLoading} />}
        />
    );
}
