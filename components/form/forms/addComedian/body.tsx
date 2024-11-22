/* eslint-disable @typescript-eslint/no-explicit-any */
import Heading from "../../../modals/heading";
import { FormInput } from "../../components/input";

interface AddNewComedianFormBodyProps {
    isLoading: boolean;
    form: any;
}

export default function AddNewComedianFormBody({
    isLoading,
    form,
}: AddNewComedianFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Add New Comedian" />
            <FormInput
                type={"text"}
                isLoading={isLoading}
                name="name"
                placeholder="Comedian name"
                form={form}
            />
        </div>
    );
}
