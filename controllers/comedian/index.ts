import { getDB } from "../../database";
import { toComedian } from "../../objects/classes/comedian/mapper";
import { toPopularityScores } from "../../util/domainModels/socialData/mapper";
import { generateComedianHash } from "../../objects/classes/comedian/hash";
import { ComedianDTO, ComedianInterface } from "../../objects/classes/comedian/comedian.interface";
import { PopularityScoreIODTO, SocialDataDTO } from "../../objects/interfaces";
import { FavoriteDTO } from "../../objects/interfaces/favoritable.interface";

const { db } = getDB();

export const addAll = async (
    comedians: ComedianDTO[],
): Promise<string[]> => {
    const hashedComedians = comedians.map((comedian: ComedianDTO) => {
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
    payload?: ComedianDTO,
): Promise<ComedianInterface[]> => {
    const task = payload?.userId
        ? db.comedians.allWithFavorites(payload.userId)
        : db.comedians.all();

    return task.then((response: ComedianDTO[] | null) =>
        response ? response.map((item: ComedianDTO) => toComedian(item)) : [],
    );
};

export const generateScores = async (): Promise<null> => {
    return db.comedians
        .getAllSocialData()
        .then((response: SocialDataDTO[] | null) => response ? toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.comedians.updateScores(popularityScores));
};

export const favoriteComedian = async (
    payload: FavoriteDTO,
    isFavorite: boolean,
): Promise<boolean> => {
    return isFavorite
        ? db.favorites.remove(payload)
        : db.favorites.add(payload);
};

export const updateSocialData = async (
    payload: SocialDataDTO,
): Promise<boolean | null> => {
    return db.comedians.updateSocialData(payload);
};

export const writeHashes = async (hashedComedians: ComedianDTO[]) => {
    return db.comedians.writeHashes(hashedComedians);
};

export const getByUUIDs = async (uuids: string[]): Promise<number[]> => {
    return db.comedians
        .getIds(uuids)
        .then((response: { id: number }[]) =>
            response.map((value: { id: number }) => value.id),
        );
};
