import { FilterSection, Selectable } from "../../interface/filter.interface";
import { TagDataDTO, TagOptionDTO } from "../../interface/tag.interface";
import { Tag } from "./Tag";

export class TagContainer implements FilterSection {
    // Properties
    id: number;
    displayName: string;
    value: string;
    options: Tag[];

    // Constructor
    constructor(input: TagDataDTO, param: string | null) {
        this.id = input.id
        this.displayName = input.display_name
        this.value = input.value
        this.options = input.options.map((option: TagOptionDTO) => {
            return new Tag(option, param?.includes(option.value))
        }).sort((a, b) => a.id > b.id ? 1 : -1)
    }

    setSelected(optionId: number) {
        const option = this.options.find((option: Selectable) => {
            return option.id == optionId
        })
        if (option) { option.select() }
    }

    asParamValue() {
        return this.options.filter((value: Tag) => value.selected).map((tag: Tag) => tag.value);
    }

}
