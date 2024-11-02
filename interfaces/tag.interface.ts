// Client
export interface TagInterface {
    id: number;
    name: string;
}

// DB
export interface GetTagDTO {
    type: string;
}

export interface GetTagResponseDTO {
    id: number;
    tag_name: string;
    type: string;
    user_facing: boolean;
}

export interface TagShowDTO {
    show_id: number;
    tag_id: number;
}

export interface TagComedianDTO {
    comedian_id: number;
    tag_id: number;
}

export interface TagClubDTO {
    club_id: number;
    tag_id: number;
}
