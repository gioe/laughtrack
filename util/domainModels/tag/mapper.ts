import {
    TagShowDTO,
    GetTagResponseDTO,
    TagInterface,
    TagComedianDTO,
    TagClubDTO,
} from "../../../interfaces";

export const toTagInterfaceArray = (
    payload: GetTagResponseDTO[],
): TagInterface[] => {
    return payload.map((item: GetTagResponseDTO) => toTagInterface(item));
};

export const toTagInterface = (payload: GetTagResponseDTO): TagInterface => {
    return {
        id: payload.id,
        name: payload.tag_name,
    };
};

export const toCreateShowTagDTOArray = (
    tags: { id: number }[],
    showId: number,
): TagShowDTO[] => {
    return tags.map((tag: { id: number }) => {
        return {
            show_id: showId,
            tag_id: tag.id,
        };
    });
};
export const toCreateComedianTagDTOArray = (
    tags: { id: number }[],
    comedianId: number,
): TagComedianDTO[] => {
    return tags.map((tag: { id: number }) => {
        return {
            comedian_id: comedianId,
            tag_id: tag.id,
        };
    });
};

export const toCreateClubTagDTOArray = (
    tags: { id: number }[],
    clubId: number,
): TagClubDTO[] => {
    return tags.map((tag: { id: number }) => {
        return {
            club_id: clubId,
            tag_id: tag.id,
        };
    });
};
