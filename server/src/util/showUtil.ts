import { Club } from "../api/interfaces/club.interface.js";

export const isLikelyShow = (inputString: string, showSignifiers?: string[]): boolean => {
  var isLikely = false;

  for (const singifier of showSignifiers ?? []) {
    if (inputString.toLowerCase().includes(singifier)) {
      isLikely = true;
    }
  }
  return isLikely
}

export const formatShowTicketLink = (ticketLink: string, club: Club): string => {
  return !ticketLink.includes("http") ? club.baseUrl + ticketLink : ticketLink
}


