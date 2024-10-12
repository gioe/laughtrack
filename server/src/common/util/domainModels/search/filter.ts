import { LineupItemDTO } from "../../../models/interfaces/lineupItem.interface.js"
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from "../../../models/interfaces/search.interface.js"
import { GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"

export const filter = (result: GetHomeSearchResultsResponseDTO,
    request: GetHomeSearchResultsDTO) => {
  
    const filteredDates = result.dates.filter((dto: GetShowResponseDTO) => {
      const names = dto.lineup.map((item: LineupItemDTO) => item.name.toLowerCase())
      const stringifiedNames = JSON.stringify(names)
  
      // const comedianIncluded = request.comedians ? stringifiedNames.includes(request.comedians.toLowerCase()) : true
      // const clubIncluded = request.clubs ? request.clubs.includes(dto.club_name.toLowerCase()) : true
  
      return true
    })
  
    return {
      ...result,
      dates: filteredDates
    }
  }