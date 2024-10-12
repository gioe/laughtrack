import { LineupItem } from "../../../models/interfaces/lineupItem.interface.js";
import { ShowInterface } from "../../../models/interfaces/show.interface.js";

export interface ComedianFilter {
    clubs?: string
    name?: string;
}

export const filterShows = (shows: ShowInterface[], filter: ComedianFilter): ShowInterface[] => {
    return shows.filter((show: ShowInterface) => {
        const names = show.lineup.map((item: LineupItem) => item.name.toLowerCase())
        const stringifiedNames = JSON.stringify(names)
        const nameMatches = filter.name ? stringifiedNames.includes(filter.name.toLowerCase()) : true;

        const clubMatches = filter.clubs ? show.clubName?.toLowerCase().includes(filter.clubs) : true

        return nameMatches && clubMatches
    })
}
