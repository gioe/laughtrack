import playwright from "playwright";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { providedStringPromise } from "../util/types/promiseUtil.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { stringIsAValidUrl } from "../util/types/urlUtil.js";
import { Scrapable } from "../types/scrapable.interface.js";

export class TicketScraper {
  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getShowTicketTask = async (scrapable: Scrapable, url?: string) => {

    if (url && stringIsAValidUrl(url)) return providedStringPromise(url)
    const page = scrapable as playwright.Page;
    return this.scraper.getHref(page, this.scrapingConfig.showTicketLinkSelector) 
  }

}
