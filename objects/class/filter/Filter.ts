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
    constructor(input: FilterDTO, paramValue: string | string[]) {
        this.id = input.id
        this.type = input.type
        this.display = input.display
        this.value = input.value
        this.selected = paramValue.includes(this.display)
    }

    handleSelection() {
        this.selected = !this.selected
    }

    asParamValue() {
        return this.selected ? this.value : ""
    }

}
