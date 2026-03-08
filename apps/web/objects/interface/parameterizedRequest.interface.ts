import { ShowSearchParams } from "./showSearch.interface";

export interface ParameterizedRequestData {
    params: ShowSearchParams;
    timezone: string;
    userId?: string;
    profileId?: string;
    slug?: string;
}
