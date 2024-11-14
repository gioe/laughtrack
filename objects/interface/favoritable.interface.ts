export interface Favoritable {
    name: string;
    isFavorite: boolean;
}

// DB
export interface FavoriteDTO {
    id: number;
    user_id: number;
}
