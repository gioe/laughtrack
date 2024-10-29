import { ShowInterface } from "../../../interfaces"

  export const sortDates = (shows: ShowInterface[], sortValue: string): ShowInterface[] => {
    return shows.sort((a: ShowInterface, b: ShowInterface) => {

      switch (sortValue) {
        case 'date': return new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime();
        default: return (b.popularityScore ?? 0) - (a.popularityScore ?? 0)
      }
    })
  }