import { Show } from "../../objects/classes/show/Show";

export const sortDates = (
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
            default:
                return (b.popularityScore ?? 0) - (a.popularityScore ?? 0);
        }
    });
};
