"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { MultiSelectComponent } from "../../select/multiSelect";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { FilterDataDTO } from "@/objects/interface";
import { Filter } from "@/objects/class/filter/Filter";
import { EntityType } from "@/objects/enum";

interface FilterParamComponentProps {
    filtersString: string;
}
export const FilterParamComponent: React.FC<FilterParamComponentProps> = ({
    filtersString,
}) => {
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const filters = JSON.parse(filtersString)
        .map((dto: FilterDataDTO) => new Filter(dto, paramsHelper))
        .filter((filter: Filter) => filter.type == EntityType.Show);

    const adjustParam = (param: string, value: number) => {
        const container = filters.find(
            (container: Filter) => container.value == param,
        );

        if (container) {
            container.handleSelection(value);
            paramsHelper.setParamValue(param, container.asParamValue());
            navigator.replaceRoute(paramsHelper.asParamsString());
        } else {
            throw new Error(
                "User selected a param value that shouldnt be there",
            );
        }
    };

    return (
        <div className="mt-4 border-t border-gray-200">
            <MultiSelectComponent
                sections={filters}
                handleValueChange={adjustParam}
            />
        </div>
    );
};
