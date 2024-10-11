import { ClubScrapingData } from "../../../models/interfaces/club.interface.js";
import { ScrapingOutput } from "../../../models/interfaces/scrape.interface.js";
import { LineupItemDTO } from "../../../models/interfaces/lineupItem.interface.js";
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from "../../../models/interfaces/search.interface.js";
import { GetShowResponseDTO } from "../../../models/interfaces/show.interface.js";
import { Show } from "../../../models/classes/Show.js";
import { writeFailureToFile } from "../../logUtil.js";


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
