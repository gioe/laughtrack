import { Selectable } from "../../interface";
import { FilterDTO } from "@/objects/interface/filter.interface";

export class Filter implements Selectable {
    // Properties
    id: number;
    name: string;
    slug: string;
    selected: boolean;

    // Constructor
    constructor(input: FilterDTO) {
        this.id = input.id
        this.name = input.name
        this.slug = input.slug
        this.selected = input.selected ?? false
    }

    handleSelection() {
        this.selected = !this.selected
    }

    asParamValue() {
        return this.selected ? this.slug : ""
    }

}
