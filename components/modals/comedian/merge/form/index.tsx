"use client";

import { FormInput } from "../../../../formComponents/input";
import Heading from "../../../heading";

interface MergeComediansFormProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
    isLoading: boolean;
}

export default function MergeComediansForm({
    isLoading,
    form,
}: MergeComediansFormProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading
                title="Merge Comedians"
                subtitle="Merge comedian with a parent entity"
            />
            <FormInput
                type={"number"}
                isLoading={isLoading}
                name="parentId"
                placeholder="Parent Id"
                form={form}
            />
        </div>
    );
}
