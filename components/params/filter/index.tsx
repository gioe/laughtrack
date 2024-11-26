"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Navigator } from "../../../objects/class/navigate/Navigator";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { FilterContainer } from "../../../objects/class/tag/FilterContainer";
import { MultiSelectComponent } from "../../select/multiSelect";

interface FilterContainerProps {
    containers: FilterContainer[];
}

export const FilterParamComponent: React.FC<FilterContainerProps> = ({
    containers,
}) => {
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const appendParam = (param: string, value: number) => {
        const container = containers.find(
            (container: FilterContainer) => container.value == param,
        );
        if (container) {
            container.setSelected(value);
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
                containers={containers}
                handleValueChange={appendParam}
            />
        </div>
    );
};
