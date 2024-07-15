import { Club } from "../../classes/Club.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { Show } from "../../types/show.interface.js";
import { buildDateFromDateTimeString } from "./dateTime.js";
import { removeSubstrings } from "./stringUtil.js";

const DATETIME_INDEX = 0
const DATE_INDEX = 1
const TIME_INDEX = 2
const NAME_INDEX = 3
const TICKET_INDEX = 4

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
    date?: string
  ): Show => {
      const dateTimeString = scrapedValues[DATETIME_INDEX]
      const dateString = date ?? scrapedValues[DATE_INDEX]
      const timeString = scrapedValues[TIME_INDEX]
      const nameString = scrapedValues[NAME_INDEX]
      const ticketString = scrapedValues[TICKET_INDEX]

      const formattedDateTime = formatShowDateTime(dateTimeString, dateString, timeString, showConfig);
      const formattedName = formatShowName(nameString);
      const formattedTicketLink = formatShowTicketLink(ticketString, club);

      return {
        clubName: club.getName(),
        dateTime: formattedDateTime,
        name: formattedName,
        ticketLink: formattedTicketLink,
      }

  }

  const formatShowDateTime = (dateTimeString: string, 
    dateString: string, 
    timeString: string, 
    showConfig: ShowHTMLConfiguration
  ): Date => {
    var newDateTimeString = dateTimeString

    if (newDateTimeString === "") {
      const formattedTimeString = formatTime(timeString, showConfig)
      newDateTimeString = dateString + formattedTimeString
    }

    return new Date()

    // return buildDateFromDateTimeString(newDateTimeString)

  }

  const formatTime = (time: string, showConfig: ShowHTMLConfiguration): string => {
    return removeSubstrings(time, showConfig.badTimeStrings ?? []);
  }

  const formatShowName = (name: string): string => {
    return name;
  }

  const formatShowTicketLink = (ticketLink: string, club: Club): string => {
    return !ticketLink.includes("http") ? club.getBaseWebsite() + ticketLink : ticketLink
  }

