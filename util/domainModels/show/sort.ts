import { ShowInterface } from "../../../interfaces";

export const sortShows = (
    shows: ShowInterface[],
    sortValue: string,
): ShowInterface[] => {
    return shows.sort((a: ShowInterface, b: ShowInterface) => {
        switch (sortValue) {
            case "date":
                return (
                    new Date(a.dateTime).getTime() -
                    new Date(b.dateTime).getTime()
                );
            case "low_to_high":
                return a.price - b.price;
            case "high_to_low":
                return b.price - a.price;
            default:
                return (b.popularityScore ?? 0) - (a.popularityScore ?? 0);
        }
    });
};
