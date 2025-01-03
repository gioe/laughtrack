import { EntityType } from "../../enum";
import { SelectionSection } from "../../interface/selectionSection.interface";
import { FilterDataDTO, FilterOptionDTO } from "../../interface/filter.interface";
import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { Selectable } from "../../interface";

export class Filter implements SelectionSection {
    // Properties
    id: number;
    display: string;
    type: EntityType;
    value: string;
    options: Selectable[];

    // Constructor
    constructor(input: FilterDataDTO, helper: SearchParamsHelper) {
        this.id = input.id
        this.type = input.type
        this.display = input.display
        this.value = input.value
        const commaSeparatedValue = helper.getParamValue(input.value)
        this.options = input.options.map((option: FilterOptionDTO) => {
            return {
                id: option.id,
                display: option.display,
                value: option.value,
                selected: commaSeparatedValue.includes(option.value)

            } as Selectable
        })
    }

    handleSelection(optionId: number) {
        this.options = this.options.map(option => ({
            ...option,
            selected: option.id === optionId ? !option.selected : option.selected
        }));
    }

    asParamValue() {
        return this.options.filter((value: Selectable) => value.selected)
            .map((option: Selectable) => option.value).join(",");
    }

}
