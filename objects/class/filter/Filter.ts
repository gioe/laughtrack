import { EntityType } from "../../enum";
import { SelectionSection } from "../../interface/selectionSection.interface";
import { FilterDataDTO, FilterOptionDTO } from "../../interface/filter.interface";
import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { FilterOption } from "./FilterOption";

export class Filter implements SelectionSection {
    // Properties
    id: number;
    display: string;
    type: EntityType;
    value: string;
    options: FilterOption[];

    // Constructor
    constructor(input: FilterDataDTO, helper: SearchParamsHelper) {
        this.id = input.id
        this.type = input.type
        this.display = input.display
        this.value = input.value

        this.options = input.options.map((option: FilterOptionDTO) => new FilterOption(option, helper))
            .sort((a, b) => a.id > b.id ? 1 : -1) ?? []

    }
    displayName: string;

    handleSelection(optionId: number) {
        this.options = this.options.map(option => option.id == optionId ? { ...option, selected: !option.selected } : option);
    }

    asParamValue() {
        return this.options.filter((value: FilterOption) => value.selected)
            .map((option: FilterOption) => option.value);
    }

}
