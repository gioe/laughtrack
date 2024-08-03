import { ElementScaper } from "./ElementScaper.js";
import { Club } from "../classes/Club.js";
import { providedStringPromise } from "../util/types/promiseUtil.js";
import Scrapable from "../types/scrapable.interface.js";

export class TicketScraper {
  private club: Club;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
  ) {
    this.club = club
  }

  getShowTicketTask = async (showComponent: Scrapable, url?: string) => {
    if (url) return providedStringPromise(url)
    return this.elementScraper.getElementCount(showComponent, this.club.showConfig.ticketLinkSelector)
      .then((count: number) => count > 0 ? this.elementScraper.getHrefFrom(showComponent, this.club.showConfig.ticketLinkSelector) : "")   
  }

}
