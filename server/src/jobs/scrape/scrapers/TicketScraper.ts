import playwright from "playwright-core";
import { ScrapingConfig } from "../../../common/models/classes/ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { providedStringPromise } from "../../../common/util/promiseUtil.js";
import { stringIsAValidUrl } from "../../../common/util/primatives/stringUtil.js";
import { Scrapable } from "../../../common/models/interfaces/scrape.interface.js";

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
