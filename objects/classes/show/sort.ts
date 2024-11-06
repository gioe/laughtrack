import { Show } from "./Show";

export const sortShows = (
    shows: Show[],
    sortValue: string,
): Show[] => {
    return shows.sort((a: Show, b: Show) => {
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
