/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { z } from "zod";
import { loginSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { FormInput } from "../../input";
import FormSubmissionButton from "../../button/form";

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

        // Include emailOptIn in the submission data
        signIn("credentials", {
            ...data,
            redirect: false,
        })
            .then((callback: any) => {
                setIsLoading(false);
                if (callback?.error) {
                    toast.error(`Error logging in`);
                } else {
                    toast.success("Logged in");
                    onSubmit();
                }
            })
            .catch((e) => {
                console.log(`THE ERROR LOOKS LIKE ${e}`);
            });
    };

    return (
        <FormProvider {...form}>
            <form
                onSubmit={form.handleSubmit(submitForm)}
                className="space-y-6"
            >
                <FormInput
                    type="email"
                    isLoading={false}
                    name={"email"}
                    label={"Email"}
                    placeholder={"Enter your email"}
                    form={form}
                />
                <FormInput
                    type="password"
                    isLoading={false}
                    name={"password"}
                    label={"Password"}
                    placeholder={"Enter password"}
                    form={form}
                />
                <FormSubmissionButton>Log In</FormSubmissionButton>
            </form>
        </FormProvider>
    );
}
