import { ClubScrapingData } from "../../../models/interfaces/club.interface.js";
import { ScrapingOutput } from "../../../models/interfaces/scrape.interface.js";
import { Show } from "../../../models/classes/Show.js";
import { writeFailureToFile } from "../../logUtil.js";

export const processShowsForStorage = (club: ClubScrapingData, shows: Show[]): ScrapingOutput[] => {
  if (shows.length == 0) writeFailureToFile(`No shows returned for ${club.name}`)

  const output = shows
    .map((show: Show) => {
      show.setClubId(club.id)
      return show;
    })
    .map((show: Show) => {
      return {
        show: show.asCreateShowDTO(),
        comedians: show.asCreateComedianDTOArray()
      } as ScrapingOutput
    })

    return output
}
