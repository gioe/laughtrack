import {
    GroupedSocialDataDTO,
    PopularityScoreIODTO,
} from "../../objects/interfaces";
import { toPopularityScores } from "../../util/domainModels/socialData/mapper";
import { getDB } from "../../database";
import { ShowDTO } from "../../objects/classes/show/show.interface";

const { db } = getDB();

export const add = async (show: ShowDTO): Promise<{ id: number }> => {
    return db.shows.add(show);
};

export const generateScores = async (): Promise<null> => {
    return db.shows
        .getAllLineupPopularityData()
        .then((response: GroupedSocialDataDTO[] | null) =>
            response ? toPopularityScores(response) : [],
        )
        .then((popularityScores: PopularityScoreIODTO[]) =>
            popularityScores.length > 0
                ? db.shows.updateScores(popularityScores)
                : null,
        );
};

export const deleteShowsForClub = async (payload: any): Promise<null> => {
    return db.shows.deleteForClub(payload);
};
