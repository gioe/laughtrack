/* eslint-disable @typescript-eslint/no-explicit-any */
import { FormInput } from "../../input/index";
import Heading from "../../modals/heading";

interface LoginFormBodyProps {
    isLoading: boolean;
    form: any;
}
export default function LoginFormBody({ isLoading, form }: LoginFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Log in" />
            <FormInput
                isLoading={isLoading}
                name={"email"}
                label={"Email"}
                type={"email"}
                placeholder={"Enter email"}
                form={form}
            />
            <FormInput
                isLoading={isLoading}
                name={"password"}
                label={"Password"}
                type={"password"}
                placeholder={"Enter password"}
                form={form}
            />
        </div>
    );
}
