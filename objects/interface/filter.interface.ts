import { EntityType } from "../enum";

// Client
export interface FilterInterface {
    id: number;
    value: string;
}

// DB
export interface FilterDTO {
    id: number;
    value: string;
    display: string;
    selected?: boolean;
    type?: string;
}
