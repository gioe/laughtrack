import { Selectable } from "../../interface";
import { FilterOptionDTO } from "../../interface/filter.interface";
import { SearchParamsHelper } from "../params/SearchParamsHelper";

export class FilterOption implements Selectable {
    // Properties
    id: number;
    display: string;
    selected: boolean;
    value: string;

    // Constructor
    constructor(option: FilterOptionDTO, helper: SearchParamsHelper) {
        this.id = option.id
        this.display = option.display
        this.value = option.value
        const paramValue = helper.getParamValue(option.display)
        console.log(paramValue)
        this.selected = paramValue ? paramValue == option.value : false
    }

}
