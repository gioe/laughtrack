/* eslint-disable @typescript-eslint/no-explicit-any */
import Heading from "../../../modals/heading";
import { FormEmailInput } from "../../components/input/email";
import { FormPasswordInput } from "../../components/input/password";

interface LoginFormBodyProps {
    isLoading: boolean;
    form: any;
}
export default function LoginFormBody({ isLoading, form }: LoginFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Welcome back" subtitle="Login to your account" />
            <FormEmailInput
                isLoading={isLoading}
                name={"email"}
                placeholder={"Email"}
                form={form}
            />
            <FormPasswordInput
                isLoading={isLoading}
                name={"password"}
                type={"password"}
                placeholder={"Password"}
                form={form}
            />
        </div>
    );
}
