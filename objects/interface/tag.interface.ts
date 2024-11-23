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
    tag_options: TagOptionDTO[];
}

export interface TagOptionDTO {
    id: number;
    name: string;
    selected?: boolean;
}
