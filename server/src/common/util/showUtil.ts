import { ClubScrapingData } from "../interfaces/client/club.interface.js";
import { ScrapingOutput } from "../interfaces/client/scrape.interface.js";
import { LineupItemDTO } from "../interfaces/data/lineupItem.interface.js";
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from "../interfaces/data/search.interface.js";
import { GetShowResponseDTO } from "../interfaces/data/show.interface.js";
import { Show } from "../models/Show.js";
import { writeFailureToFile } from "./logUtil.js";

export const orderDates = (shows: GetShowResponseDTO[] | undefined, sortValue?: string): GetShowResponseDTO[] => {
  if (shows == undefined) return []
  return shows.sort((a: GetShowResponseDTO, b: GetShowResponseDTO) => {
    if (sortValue == 'date') return new Date(a.date_time).getTime() - new Date(b.date_time).getTime();
    else return (b.popularity_score ?? 0) - (a.popularity_score ?? 0)
  })
}

export const isLikelyShow = (inputString: string, showSignifiers?: string[]): boolean => {
  var isLikely = false;

  for (const singifier of showSignifiers ?? []) {
    if (inputString.toLowerCase().includes(singifier)) {
      isLikely = true;
    }
  }
  return isLikely
}

export const processShowsForStorage = (club: ClubScrapingData, shows: Show[]): ScrapingOutput[] => {
  if (shows.length == 0) writeFailureToFile(`No shows returned for ${club.name}`)

  return shows
    .map((show: Show) => {
      show.setClubId(club.id)
      return show;
    })
    .map((show: Show) => {
      const showDto = show.asCreateShowDTO()
      const comedianArrayDto = show.asCreateComedianDTOArray()

      if (showDto !== null && comedianArrayDto.length > 0) {
        return {
          show: show.asCreateShowDTO(),
          comedians: show.asCreateComedianDTOArray()
        } as ScrapingOutput
      }
      return null
    })
    .filter((value: ScrapingOutput | null) => value !== null)
}

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
    dates: orderDates(filteredDates, request.sort)
  }
}