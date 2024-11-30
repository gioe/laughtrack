/* eslint-disable @typescript-eslint/no-explicit-any */

import { usePageContext } from "../../../../contexts/PageEntityProvider";
import { useDataProvider } from "../../../../contexts/EntityPageDataProvider";
import { Filter } from "../../../../objects/class/tag/Filter";
import { MultiSelectComponent } from "../../../select/multiSelect";
interface TagEntityFormBodyProps {
    form: any;
}

export default function TagEntityFormBody({ form }: TagEntityFormBodyProps) {
    const { filters } = useDataProvider();
    const { primaryEntity } = usePageContext();
    console.log(filters);
    return (
        <div className="flex flex-col gap-4">
            <MultiSelectComponent
                form={form}
                sections={filters.filter(
                    (filter: Filter) => filter.type === primaryEntity,
                )}
            />
        </div>
    );
}
