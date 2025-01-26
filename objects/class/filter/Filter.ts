import { EntityType } from "../../enum";
import { SelectionSection } from "../../interface/selectionSection.interface";
import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { Selectable } from "../../interface";
import { FilterDTO } from "@/objects/interface/filter.interface";

export class Filter implements Selectable {
    // Properties
    id: number;
    display: string;
    type: string;
    value: string;
    selected: boolean;

    // Constructor
    constructor(input: FilterDTO, helper: SearchParamsHelper) {
        const commaSeparatedValue = helper.getParamValue('filters')
        this.id = input.id
        this.type = input.type
        this.display = input.display
        this.value = input.value
        this.selected = commaSeparatedValue.includes(this.value)
    }

    handleSelection(optionId: number) {
        this.selected = this.id === optionId ? !this.selected : this.selected
    }

    asParamValue() {
        return this.selected ? this.value : ""
    }

}
