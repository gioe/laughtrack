import { Comedian } from "./Comedian";

export const filterComedians = (
    comedians: Comedian[],
    filter: Comedian,
): Comedian[] => {
    return comedians.filter((comedian: Comedian) => {
        const nameMatches = filter.name
            ? comedian.name.toLowerCase().includes(filter.name.toLowerCase())
            : true;
        return nameMatches;
    });
};
