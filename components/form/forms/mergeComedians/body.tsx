/* eslint-disable @typescript-eslint/no-explicit-any */
import Heading from "../../../modals/heading";
import { FormInput } from "../../components/input";

interface MergeComediansFormBodyProps {
    isLoading: boolean;
    form: any;
}

export default function MergeComediansFormBody({
    isLoading,
    form,
}: MergeComediansFormBodyProps) {
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
