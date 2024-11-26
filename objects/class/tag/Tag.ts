import { Selectable } from "../../interface/filter.interface";
import { TagOptionDTO } from "../../interface/tag.interface";

export class Tag implements Selectable {
    // Properties
    id: number;
    displayName: string;
    selected: boolean;
    value: string;

    // Constructor
    constructor(input: TagOptionDTO, selected?: boolean) {
        this.id = input.id
        this.displayName = input.display_name
        this.value = input.value
        this.selected = input.selected ?? (selected ?? false)
    }

    select() {
        this.selected = !this.selected
    }

}
