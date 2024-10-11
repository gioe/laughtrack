import { LineupItemDTO } from "../../../models/interfaces/lineupItem.interface.js"
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from "../../../models/interfaces/search.interface.js"
import { GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"

export const filterAndSort = (result: GetHomeSearchResultsResponseDTO,
    request: GetHomeSearchResultsDTO) => {
  
    const filteredDates = result.dates.filter((dto: GetShowResponseDTO) => {
      const names = dto.lineup.map((item: LineupItemDTO) => item.name.toLowerCase())
      const stringifiedNames = JSON.stringify(names)
  
      const comedianIncluded = request.comedians ? stringifiedNames.includes(request.comedians.toLowerCase()) : true
      const clubIncluded = request.clubs ? request.clubs.includes(dto.club_name.toLowerCase()) : true
  
      return clubIncluded && comedianIncluded
    })
  
    return {
      ...result,
      dates: sortDates(filteredDates, request.sort)
    }
  }

  export const sortDates = (shows: GetShowResponseDTO[] | undefined, sortValue?: string): GetShowResponseDTO[] => {
    if (shows == undefined) return []
    return shows.sort((a: GetShowResponseDTO, b: GetShowResponseDTO) => {
      if (sortValue == 'date') return new Date(a.date_time).getTime() - new Date(b.date_time).getTime();
      else return (b.popularity_score ?? 0) - (a.popularity_score ?? 0)
    })
  }