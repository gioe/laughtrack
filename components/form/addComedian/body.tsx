/* eslint-disable @typescript-eslint/no-explicit-any */
import { FormTextInput } from "../../input/text";
import Heading from "../../modals/heading";

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
            <FormTextInput
                isLoading={isLoading}
                name="name"
                placeholder="Comedian name"
                form={form}
            />
        </div>
    );
}
