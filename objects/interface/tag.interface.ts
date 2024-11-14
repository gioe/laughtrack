// Client
export interface TagInterface {
    id: number;
    name: string;
}

// DB
export interface TagDTO {
    id: number;
    tag_name: string;
    type: string;
    user_facing: boolean;
}
