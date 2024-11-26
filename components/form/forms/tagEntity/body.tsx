/* eslint-disable @typescript-eslint/no-explicit-any */

import { FilterContainer } from "../../../../objects/class/tag/FilterContainer";
import { MultiSelectComponent } from "../../../select/multiSelect";

interface TagEntityFormBodyProps {
    tagContainers: FilterContainer[];
    form: any;
}

export default function TagEntityFormBody({
    form,
    tagContainers,
}: TagEntityFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <MultiSelectComponent form={form} containers={tagContainers} />
        </div>
    );
}
