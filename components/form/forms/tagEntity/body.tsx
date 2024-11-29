/* eslint-disable @typescript-eslint/no-explicit-any */

import { usePageContext } from "../../../../contexts/EntityContext";
import { useDataProvider } from "../../../../contexts/EntityDataContext";
import { Filter } from "../../../../objects/class/tag/Filter";
import { MultiSelectComponent } from "../../../select/multiSelect";

interface TagEntityFormBodyProps {
    form: any;
}

export default function TagEntityFormBody({ form }: TagEntityFormBodyProps) {
    const { filters } = useDataProvider();
    const { primaryEntity } = usePageContext();
    return (
        <div className="flex flex-col gap-4">
            <MultiSelectComponent
                form={form}
                sections={filters.filter(
                    (filter: Filter) => filter.value === primaryEntity,
                )}
            />
        </div>
    );
}
