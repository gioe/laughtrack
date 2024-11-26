// Client
export interface TagInterface {
    id: number;
    value: string;
}

// DB
export interface TagDataDTO {
    id: number;
    value: string;
    display_name: string;
    options: TagOptionDTO[];
}

export interface TagOptionDTO {
    id: number;
    value: string;
    display_name: string;
    selected?: boolean;
}
