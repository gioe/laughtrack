import { ElementScaper } from "./ElementScaper.js";
import { Club } from "../classes/Club.js";
import { providedStringPromise } from "../util/types/promiseUtil.js";
import Scrapable from "../types/scrapable.interface.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";

export class TicketScraper {
  private scrapingConfig: ScrapingConfig;
  private elementScraper = new ElementScaper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getShowTicketTask = async (showComponent: Scrapable, url?: string) => {
    if (url) return providedStringPromise(url)
    return this.elementScraper.getElementCount(showComponent, this.scrapingConfig.ticketLinkSelector)
      .then((count: number) => count > 0 ? this.elementScraper.getHref(showComponent, this.scrapingConfig.ticketLinkSelector) : "")   
  }

}
