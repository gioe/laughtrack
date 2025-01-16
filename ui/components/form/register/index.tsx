/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { registerSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FormInput } from "../../input/index";
import { FormProvider, useForm } from "react-hook-form";
import { Divider } from "../../divider";
import SocialAuthButtons from "../../auth/social";
import FormSubmissionButton from "../../button/form";

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

    const submitForm = async (data: z.infer<typeof registerSchema>) => {
        try {
            setIsLoading(true);
            const response = await fetch("/api/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                throw new Error("Registration failed");
            }

            const callback = await signIn("credentials", {
                ...data,
                redirect: false,
            });

            if (callback?.error) {
                toast.error("Something went wrong");
            } else {
                toast.success("Logged in");
                onSubmit();
            }
        } catch (error) {
            toast.error("Something went wrong");
        } finally {
            setIsLoading(false);
        }
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
                    placeholder={"Enter your email..."}
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
                <FormInput
                    type="zipCode"
                    isLoading={false}
                    name={"zipCode"}
                    label={"Zip Code"}
                    placeholder={
                        "Enter your zip code. We use this to find shows around you."
                    }
                    form={form}
                />

                <Divider text="or" />

                <SocialAuthButtons
                    onAppleClick={() => {}}
                    onGoogleClick={() => {}}
                />

                {/* Login Button */}
                <FormSubmissionButton>Sign Up</FormSubmissionButton>
            </form>
        </FormProvider>
    );
}
