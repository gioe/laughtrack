import {
    GroupedPopularityScoreDTO,
    PopularityScoreIODTO,
    CreateShowDTO,
} from "../../interfaces";
import { toPopularityScores } from "../../util/domainModels/socialData/mapper";
import { db } from "../../database";

export const add = async (show: CreateShowDTO): Promise<{ id: number }> => {
    return db.shows.add(show);
};

export const generateScores = async (): Promise<null> => {
    return db.shows
        .getAllLineupPopularityData()
        .then((response: GroupedPopularityScoreDTO[] | null) =>
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
