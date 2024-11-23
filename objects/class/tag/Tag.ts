import { FilterSection, Selectable } from "../../interface/filter.interface";
import { TagDataDTO, TagOptionDTO } from "../../interface/tag.interface";

export class TagData implements FilterSection {
    // Properties
    id: number;
    name: string;
    value: string;
    options: Selectable[];

    // Constructor
    constructor(input: TagDataDTO) {
        this.id = input.id
        this.name = input.name
        this.value = input.param_value
        this.options = input.tag_options.map((option: TagOptionDTO) => {
            return {
                id: option.id,
                name: option.name,
                selected: option.selected ?? false
            }
        })
    }

}
