export interface Favoritable {
    name: string;
    isFavorite: boolean;
}

// DB
export interface FavoriteDTO {
    id: number;
    user_id: number;
}

export interface AddFavoriteDTO {
    is_favorite: boolean
    comedian_id: string;
    user_id: number;
}

