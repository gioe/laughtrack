// Client
export interface FilterInterface {
    id: number;
    value: string;
}

// DB
export interface FilterDTO {
    id: number;
    slug: string;
    name: string;
    selected?: boolean;
}
