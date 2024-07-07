import { Club } from "../../classes/Club.js";
import { Show } from "../../types/show.interface.js";
import { buildDateFromDateTimeString } from "./dateTime.js";


export const buildShowFromScrapedElements = (scrapedValues: string[], club: Club): Show => {
  const formattedDateTime = formatShowDateTimes(scrapedValues[0], scrapedValues[1], scrapedValues[2]);
  const formattedName = formatShowName(scrapedValues[3]);
  const formattedTicketLinke = formatShowTicketLink(scrapedValues[4]);
  
  return {
    clubName: club.name,
    clubWebsite: club.homePage,
    dateTime: formattedDateTime,
    name: formattedName,
    ticketLink: formattedTicketLinke, 
  } as Show

}

const formatShowDateTimes = (dateTime: string, date: string, time: string): Date => {

  if (dateTime) {
    return buildDateFromDateTimeString(dateTime)
  }
  //TODO: Handle cases where the date and time are separate strings
  return new Date()
}

const formatShowName = (name: string): string => {
  return "";
}

const formatShowTicketLink = (ticketLink: string): string => {
  return ticketLink
}

export const isLikelyShow = (inputString: string, showSignifiers: string[]): boolean => {
  var isLikely = false;
  for (const singifier of showSignifiers) {
    if (inputString.toLowerCase().includes(singifier)) {
      isLikely = true;
    }
  }
  return isLikely
}