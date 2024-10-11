import { ClubScrapingData } from "../interfaces/client/club.interface.js";
import { ScrapingOutput } from "../interfaces/client/scrape.interface.js";
import { ShowInterface } from "../interfaces/client/show.interface.js";
import { Show } from "../models/Show.js";
import { writeFailureToFile } from "./logUtil.js";

export const orderShows = (shows: ShowInterface[] | undefined, sortValue?: string): ShowInterface[] => {
  if (shows == undefined) return []
  return shows.sort((a: ShowInterface, b: ShowInterface) => {
    if (sortValue == 'date') return new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime();
    else return (b.popularityScore ?? 0) - (a.popularityScore ?? 0)
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

