import { LineupItem } from "../../../models/interfaces/lineupItem.interface.js";
import { ShowInterface } from "../../../models/interfaces/show.interface.js";

export interface ComedianFilter {
  name?: string;
}

export const filterShows = (shows: ShowInterface[], filter: ComedianFilter): ShowInterface[] => {
  return shows.filter((club: ShowInterface) => {
    const names = club.lineup.map((item: LineupItem) => item.name.toLowerCase())
    const stringifiedNames = JSON.stringify(names)
    const nameMatches = filter.name ? stringifiedNames.includes(filter.name.toLowerCase()) : true;
    return nameMatches
  })
}
