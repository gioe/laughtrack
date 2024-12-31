"use client";

import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { registerSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import axios from "axios";
import { FormInput } from "../../input/index";
import Heading from "../../modals/heading";
import { FormProvider, useForm } from "react-hook-form";
import { FullRoundedButton } from "../../button/rounded/full";

interface RegistrationFormProps {
    onSubmit: () => void;
    onClose: () => void;
    handleLoginClick: () => void;
}

export default function RegistrationForm({
    onSubmit,
    onClose,
    handleLoginClick,
}: RegistrationFormProps) {
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
                if (callback?.error) {
                    toast.error("Something went wrong");
                } else {
                    toast.success("Logged in");
                    onSubmit();
                }
            });
    };

    return (
        <div className="flex items-center w-full justify-evenly m-12">
            <div className="flex flex-col justify-center m-3 basis-1/2">
                <Heading title="Sign up" />
                <FormProvider {...form}>
                    <form onSubmit={form.handleSubmit(submitForm)}>
                        <div className="pt-5">
                            <FormInput
                                isLoading={isLoading}
                                name={"email"}
                                label={"Email"}
                                placeholder={"Enter email"}
                                form={form}
                            />
                        </div>
                        <div className="pt-5">
                            <FormInput
                                isLoading={isLoading}
                                name={"password"}
                                label={"Password"}
                                placeholder={"Enter password"}
                                form={form}
                            />
                        </div>
                        <div className="flex flex-col gap-2 pt-5">
                            <FullRoundedButton label="OK" />
                            <FullRoundedButton
                                type="button"
                                handleClick={onClose}
                                label="Close"
                            />
                        </div>
                    </form>
                </FormProvider>
            </div>
            <div className="flex flex-col basis-1/2 gap-10 justify-center p-5">
                <h1 className="text-copper font-fjalla text-l text-center">
                    Already have an account?
                </h1>
                <FullRoundedButton
                    type="button"
                    handleClick={handleLoginClick}
                    label="Log In"
                />
            </div>
        </div>
    );
}
