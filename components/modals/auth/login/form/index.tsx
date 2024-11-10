"use client";

import { FormInput } from "../../../../formComponents/input";
import Heading from "../../../heading";

interface LoginFormProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}
export default function LoginForm({ isLoading, form }: LoginFormProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Welcome back" subtitle="Login to your account" />
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
    );
}
