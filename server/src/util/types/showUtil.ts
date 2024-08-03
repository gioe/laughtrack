import { Club } from "../../classes/Club.js";
import { ScrapedShow } from "../../types/scrapedShow.interface.js";
import { Show } from "../../types/show.interface.js";

export const isLikelyShow = (inputString: string, showSignifiers?: string[]): boolean => {
  var isLikely = false;
 
  if (showSignifiers) {
    for (const singifier of showSignifiers) {
      if (inputString.toLowerCase().includes(singifier)) {
        isLikely = true;
      }
    }
  }
  
  return isLikely
  }

  export const createShow = (
    scrapedShow: ScrapedShow, 
    club: Club, 
  ): Show => {
   
      const dateTime = scrapedShow.dateTimeContainer.asDateObject()
      const ticketLink = formatShowTicketLink(scrapedShow.ticketString, club);
      
      return {
        clubName: club.name,
        dateTime,
        ticketLink,
      }

  }

  const formatShowTicketLink = (ticketLink: string, club: Club): string => {
    return !ticketLink.includes("http") ? club.baseWebsite + ticketLink : ticketLink
  }


