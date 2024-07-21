import { Club } from "../../classes/Club.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { Show } from "../../types/show.interface.js";
import { buildDate, formatTimeString, } from "./dateTime.js";
import { removeBadWhiteSpace, removeSubstrings } from "./stringUtil.js";

export const isLikelyShow = (inputString: string, showSignifiers: string[]): boolean => {
    var isLikely = false;
    for (const singifier of showSignifiers) {
      if (inputString.toLowerCase().includes(singifier)) {
        isLikely = true;
      }
    }
    return isLikely
  }

  export const createShow = (scrapedValues: string[], 
    club: Club, 
    showConfig: ShowHTMLConfiguration,
  ): Show => {

      const dateTimeString = scrapedValues[0]
      const nameString = scrapedValues[1]
      const ticketString = scrapedValues[2]

      const formattedDateTime = buildDate(dateTimeString, showConfig.timezone)
      const formattedName = formatShowName(nameString);
      const formattedTicketLink = formatShowTicketLink(ticketString, club);

      return {
        clubName: club.getName(),
        dateTime: formattedDateTime,
        name: formattedName,
        ticketLink: formattedTicketLink,
      }

  }

  const formatShowName = (name: string): string => {
    return name;
  }

  const formatShowTicketLink = (ticketLink: string, club: Club): string => {
    return !ticketLink.includes("http") ? club.getBaseWebsite() + ticketLink : ticketLink
  }

  export const normalizeDatetime = (datetime: string) => {
    return removeBadWhiteSpace(datetime);
  }

  export const combinedScrapedDatesAndTime =  (scrapedValues: string[], showConfig: ShowHTMLConfiguration) => {
    const dateString = scrapedValues[0]
    const cleanedDate = "";
    
    const cleanedTime = removeSubstrings(scrapedValues[1], showConfig.badTimeStrings ?? []);
    const formattedTime = formatTimeString(cleanedTime)

    return ""
}

