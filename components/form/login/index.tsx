/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { z } from "zod";
import { loginSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import Heading from "../../modals/heading";
import { FormInput } from "../../input";
import { FullRoundedButton } from "../../button/rounded/full";

interface LoginFormProps {
    onSubmit: () => void;
    onClose: () => void;
}
export default function LoginForm({ onSubmit, onClose }: LoginFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof loginSchema>>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const submitForm = (data: z.infer<typeof loginSchema>) => {
        console.log(data);
        setIsLoading(true);

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
                console.log(`THE ERROR LOOkS LIKE ${e}`);
            });
    };

    return (
        <div className="flex items-center w-full justify-evenly">
            <div className="flex flex-col justify-center m-12 basis-1/2">
                <Heading title="Log in" />
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
            <div className="flex flex-col basis-1/2 gap-10 justify-start m-10">
                <h1 className="text-copper font-fjalla text-m text-center">
                    Laughtrack exists to get you out of the house.
                    <br />
                    Find funny shows.
                    <br />
                    Follow funny comedians.
                    <br />
                    Get informed when funny comedians put on funny shows.
                    <br />
                    Turn off that podcast and go see the real thing.
                </h1>
            </div>
        </div>
    );
}
