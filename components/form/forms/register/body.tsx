/* eslint-disable @typescript-eslint/no-explicit-any */
import Heading from "../../../modals/heading";
import { FormInput } from "../../components/input";

interface RegisterFormBodyProps {
    isLoading: boolean;
    form: any;
}
export default function RegisterFormBody({
    isLoading,
    form,
}: RegisterFormBodyProps) {
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
