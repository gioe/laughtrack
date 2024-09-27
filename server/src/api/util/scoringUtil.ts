import { ComedianInterface } from "../../common/interfaces/comedian.interface.js";
import { ShowInterface } from "../../common/interfaces/show.interface.js";

export const generateClubPopularityData = (shows: ShowInterface[]): number => {
    return shows.map((show: ShowInterface) => generateShowPopularityData(show.comedians ?? []))
    .reduce((partialSum, a) => partialSum + a, 0);
}

export const generateShowPopularityData = (comedians: ComedianInterface[]): number => {
    return comedians.map((comedian: ComedianInterface) => generateComedianPopularityScore(comedian))
    .reduce((partialSum, a) => partialSum + a, 0);
}

export const generateComedianPopularityScore = (comedian: ComedianInterface): number => {
    const instagramScore = (comedian.instagramFollowers ?? 0) * 0.8;
    const tikTokScore = (comedian.tiktokFollowers ?? 0) * 0.9
    const socialScore = (instagramScore + tikTokScore) / 2

    return comedian.isPseudonym ? socialScore * 1.5 : socialScore
}



