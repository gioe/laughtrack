import { SearchParams } from "./showSearch.interface";

export interface ParameterizedRequestData {
    params: SearchParams;
    timezone: string;
    userId?: string;
    profileId?: string;
    slug?: string;
    isAdmin?: boolean;
}
