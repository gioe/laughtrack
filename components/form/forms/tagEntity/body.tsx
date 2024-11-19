/* eslint-disable @typescript-eslint/no-explicit-any */

import { FormSelectable } from "../../../../objects/interface";
import { CheckboxFormComponent } from "../../components/checkbox";

interface TagEntityFormBodyProps {
    tags: FormSelectable[];
    form: any;
}

export default function TagEntityFormBody({
    form,
    tags,
}: TagEntityFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <CheckboxFormComponent items={tags} form={form} name={"tagIds"} />
        </div>
    );
}
