import { getDB } from "../../database";
import {
    toComedian,
    toComedianFilter,
} from "../../util/domainModels/comedian/mapper";
import {
    CreateComedianDTO,
    GetComediansDTO,
    GetComedianResponseDTO,
    ComedianInterface,
    ComedianFilterInterface,
    UpdateComedianHashDTO,
    CreateFavoriteDTO,
    GetSocialDataDTO,
    PopularityScoreIODTO,
    UpdateSocialDataDTO,
} from "../../interfaces";
import { toPopularityScores } from "../../util/domainModels/socialData/mapper";
import { generateComedianHash } from "../../util/domainModels/comedian/hash";

const { db } = getDB();

export const addAll = async (
    comedians: CreateComedianDTO[],
): Promise<string[]> => {
    const hashedComedians = comedians.map((comedian: CreateComedianDTO) => {
        return {
            name: comedian.name,
            uuid_id: generateComedianHash(comedian.name),
        };
    });

    return db.comedians
        .addAll(hashedComedians)
        .then(() => hashedComedians.map((comedian) => comedian.uuid_id));
};

export const getAllComedians = async (
    payload?: GetComediansDTO,
): Promise<ComedianInterface[]> => {
    const task = payload?.userId
        ? db.comedians.allWithFavorites(payload.userId)
        : db.comedians.all();

    return task.then((response: GetComedianResponseDTO[] | null) =>
        response ? response.map((item: any) => toComedian(item)) : [],
    );
};

export const generateScores = async (): Promise<null> => {
    return db.comedians
        .getAllSocialData()
        .then((response: GetSocialDataDTO[] | null) =>
            response ? toPopularityScores(response) : [],
        )
        .then((popularityScores: PopularityScoreIODTO[]) =>
            db.comedians.updateScores(popularityScores),
        );
};

export const favoriteComedian = async (
    payload: CreateFavoriteDTO,
    isFavorite: boolean,
): Promise<boolean> => {
    return isFavorite
        ? db.favorites.remove(payload)
        : db.favorites.add(payload);
};

export const updateSocialData = async (
    payload: UpdateSocialDataDTO,
): Promise<boolean | null> => {
    return db.comedians.updateSocialData(payload);
};

export const getAllComedianFilters = async (): Promise<
    ComedianFilterInterface[]
> => {
    return db.comedians
        .all()
        .then((response: GetComedianResponseDTO[] | null) =>
            response ? response.map((item: any) => toComedianFilter(item)) : [],
        );
};

export const writeHashes = async (hashedComedians: UpdateComedianHashDTO[]) => {
    return db.comedians.writeHashes(hashedComedians);
};

export const getByUUIDs = async (uuids: string[]): Promise<number[]> => {
    return db.comedians
        .getIds(uuids)
        .then((response: { id: number }[]) =>
            response.map((value: { id: number }) => value.id),
        );
};
