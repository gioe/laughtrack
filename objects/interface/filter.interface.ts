import { EntityType } from "../enum";

// Client
export interface FilterInterface {
    id: number;
    value: string;
}

// DB
export interface FilterDataDTO {
    id: number;
    display: string;
    value: string;
    type: EntityType,
    options: FilterOptionDTO[];
}

export interface FilterOptionDTO {
    id: number;
    value: string;
    display: string;
    selected?: boolean;
}
