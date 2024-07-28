import { Club } from "../../classes/Club.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { ScrapedShow } from "../../types/scrapedShow.interfac.js";
import { Show } from "../../types/show.interface.js";
import { createDateObject } from "./dateTimeUtil.js";
import { removeBadWhiteSpace } from "./stringUtil.js";

export const isLikelyShow = (inputString: string, showSignifiers: string[]): boolean => {
    var isLikely = false;
    for (const singifier of showSignifiers) {
      if (inputString.toLowerCase().includes(singifier)) {
        isLikely = true;
      }
    }
    return isLikely
  }

  export const createShow = (
    scrapedShow: ScrapedShow, 
    club: Club, 
    showConfig: ShowHTMLConfiguration,
  ): Show => {
 
      const dateTime = createDateObject(scrapedShow.dateTimeString, showConfig.timezone)
      const name = formatShowName(scrapedShow.nameString);
      const ticketLink = formatShowTicketLink(scrapedShow.ticketString, club);

      return {
        clubName: club.getName(),
        dateTime,
        name,
        ticketLink,
      }

  }

  const formatShowName = (name: string): string => {
    return removeBadWhiteSpace(name);
  }

  const formatShowTicketLink = (ticketLink: string, club: Club): string => {
    return !ticketLink.includes("http") ? club.getBaseWebsite() + ticketLink : ticketLink
  }


