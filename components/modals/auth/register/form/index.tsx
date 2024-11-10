"use client";

import { FormInput } from "../../../../formComponents/input";
import Heading from "../../../heading";

interface RegistrationFormProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function RegistrationForm({
    isLoading,
    form,
}: RegistrationFormProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading
                title="Welcome to Laughtrack"
                subtitle="Create an account"
            />
            <FormInput
                form={form}
                type="text"
                name="email"
                placeholder="Email"
                isLoading={isLoading}
            />
            <FormInput
                form={form}
                name="password"
                type="password"
                placeholder="Password"
                isLoading={isLoading}
            />
        </div>
    );
}
