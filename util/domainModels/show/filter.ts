import { ShowInterface, ComedianInterface } from "../../../interfaces";

export interface ComedianFilter {
    clubs?: string
    name?: string;
}

export const filterShows = (shows: ShowInterface[], filter: ComedianFilter): ShowInterface[] => {
    return shows.filter((show: ShowInterface) => {
        const names = show.lineup.map((item: ComedianInterface) => item.name.toLowerCase())
        const stringifiedNames = JSON.stringify(names)
        const nameMatches = filter.name ? stringifiedNames.includes(filter.name.toLowerCase()) : true;

        const clubMatches = filter.clubs ? show.clubName?.toLowerCase().includes(filter.clubs) : true

        return nameMatches && clubMatches
    })
}
