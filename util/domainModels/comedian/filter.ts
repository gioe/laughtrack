import { ComedianInterface } from "../../../interfaces";

export const filterComedians = (
    comedians: ComedianInterface[],
    filter: ComedianInterface,
): ComedianInterface[] => {
    return comedians.filter((comedian: ComedianInterface) => {
        const nameMatches = filter.name
            ? comedian.name.toLowerCase().includes(filter.name.toLowerCase())
            : true;
        return nameMatches;
    });
};
