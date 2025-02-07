import {  QueryProperty } from "@/objects/enum";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { SortOptionInterface } from "@/objects/interface";

export const getDefaultSortingOption = (sortOptions: SortOptionInterface[], paramsHelper: SearchParamsHelper) => {
    return sortOptions.find(
        (value) =>
            value.value == paramsHelper.getParamValue(QueryProperty.Sort) &&
            value.direction ==
            paramsHelper.getParamValue(QueryProperty.Direction),
    ) ?? sortOptions[0]

}
