import {
    ComedianFilterInterface,
    ComedianInterface,
    GetComedianResponseDTO,
    GetComediansDTO,
    UpdateComedianRelationshipDTO,
} from "../../../interfaces";
import { toDates } from "../show/mapper";
import { toSocialDataInterface } from "../socialData/mapper";

export const toLineup = (
    payload: GetComedianResponseDTO[],
): ComedianInterface[] => {
    return payload.map((item: any) => toComedian(item));
};

export const toComedian = (
    payload: GetComedianResponseDTO,
): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialDataInterface(payload.social_data),
        dates: toDates(payload.dates),
        isFavorite: payload.is_favorite ?? false,
        tags: [],
    };
};

export const toComedianFilter = (
    payload: GetComedianResponseDTO,
): ComedianFilterInterface => {
    return {
        id: payload.id,
        name: payload.name,
    };
};

export const toGetComediansDTO = (payload: any): GetComediansDTO => {
    return {
        userId:
            payload.currentUser.id == "" ? undefined : payload.currentUser.id,
    };
};

export const toUpdateComedianRelationshipDTO = (
    payload: any,
): UpdateComedianRelationshipDTO => {
    return {
        parent_id: Number(payload.parentId),
        child_id: Number(payload.childId),
    };
};
