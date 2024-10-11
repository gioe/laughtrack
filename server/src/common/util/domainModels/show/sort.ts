import { GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"

  export const sortDates = (shows: GetShowResponseDTO[] | undefined, sortValue?: string): GetShowResponseDTO[] => {
    if (shows == undefined) return []
    return shows.sort((a: GetShowResponseDTO, b: GetShowResponseDTO) => {
      if (sortValue == 'date') return new Date(a.date_time).getTime() - new Date(b.date_time).getTime();
      else return (b.popularity_score ?? 0) - (a.popularity_score ?? 0)
    })
  }