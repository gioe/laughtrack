import { SortProperty } from "../../../util/enum";
import { Show } from "./Show";

export const sortShows = (
    shows: Show[],
    sortValue: SortProperty,
): Show[] => {
    return shows.sort((a: Show, b: Show) => {
        switch (sortValue) {
            case SortProperty.Date:
                return (
                    new Date(a.dateTime).getTime() -
                    new Date(b.dateTime).getTime()
                );
            case SortProperty.LowToHigh: return a.price - b.price;
            case SortProperty.HighToLow: return b.price - a.price;
            default: return (b.popularityScore ?? 0) - (a.popularityScore ?? 0);
        }
    });
};
