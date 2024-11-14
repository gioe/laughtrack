/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import Heading from "../../../modals/heading";
import { FormInput } from "../../components/input";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { loginSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import BaseForm from "..";
import { ButtonType } from "../../../../objects/enum";

interface LoginFormProps {
    onSubmit: () => void;
}
export default function LoginForm({ onSubmit }: LoginFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof loginSchema>>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            username: "",
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
            body={
                <div className="flex flex-col gap-4">
                    <Heading
                        title="Welcome back"
                        subtitle="Login to your account"
                    />
                    <FormInput
                        isLoading={isLoading}
                        type={"text"}
                        name={"email"}
                        placeholder={"Email"}
                        form={form}
                    />
                    <FormInput
                        isLoading={isLoading}
                        name={"password"}
                        type={"password"}
                        placeholder={"Password"}
                        form={form}
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
