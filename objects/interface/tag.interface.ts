import { EntityType } from "../enum";

// Client
export interface TagInterface {
    id: number;
    value: string;
}

// DB
export interface TagDataDTO {
    id: number;
    display_name: string;
    value: string;
    type: EntityType,
    options: TagOptionDTO[];
}

export interface TagOptionDTO {
    id: number;
    value: string;
    display_name: string;
    selected?: boolean;
}
