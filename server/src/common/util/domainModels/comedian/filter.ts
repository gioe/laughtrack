import { ClubInterface } from "../../../models/interfaces/club.interface.js";
import { ComedianInterface } from "../../../models/interfaces/comedian.interface.js";

export const filterComedians = (comedians: ComedianInterface[], filter: ComedianInterface): ComedianInterface[] => {
  return comedians.filter((comedian: ComedianInterface) => {
    const nameMatches = filter.name ? comedian.name.toLowerCase().includes(filter.name.toLowerCase()) : true;
    return nameMatches
  })
}