// Client
export interface TagInterface {
    id: number;
    name: string;
}

// DB
export interface TagDataDTO {
    id: number;
    name: string;
    param_value: string;
    options: TagOptionDTO[];
}

export interface TagOptionDTO {
    id: number;
    name: string;
    selected?: boolean;
}
