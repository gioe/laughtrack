/* eslint-disable @typescript-eslint/no-explicit-any */

import { Filter } from "../../../../objects/class/tag/Filter";
import { MultiSelectComponent } from "../../../select/multiSelect";

interface TagEntityFormBodyProps {
    filterSections: Filter[];
    form: any;
}

export default function TagEntityFormBody({
    form,
    filterSections,
}: TagEntityFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <MultiSelectComponent form={form} sections={filterSections} />
        </div>
    );
}
