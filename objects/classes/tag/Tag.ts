import { TagDTO, TagInterface } from "../../interfaces";

export class Tag implements TagInterface {
    // Properties
    id: number;
    name: string;

    // Constructor
    constructor(input: TagDTO) {
        this.id = input.id
        this.name = input.tag_name
    }

}
