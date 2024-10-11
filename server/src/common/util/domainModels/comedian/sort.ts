import { ComedianInterface } from "../../../models/interfaces/comedian.interface.js";

export const sortComedians = (comedians: ComedianInterface[], sortValue?: string): ComedianInterface[] => {
    return comedians.sort((a: ComedianInterface, b: ComedianInterface) => {
        if (sortValue == 'alphabetical') return a.name < b.name ? -1 : 1;
        else return (b.popularityScore ?? 0) - (a.popularityScore ?? 0)
    })
}