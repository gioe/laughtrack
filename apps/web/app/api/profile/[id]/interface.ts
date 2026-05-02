export interface UserProfileInterface {
    email?: string;
    name?: string;
    image?: string;
    zipCode?: string | null;
    nearbyDistanceMiles?: number | null;
    emailOptin?: boolean;
    pushOptin?: boolean;
    id?: string;
    userId?: string;
    role?: string;
}
