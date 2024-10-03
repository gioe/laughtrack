import playwright from "playwright-core";
import { ScrapingConfig } from "../../common/models/ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { Scrapable } from "../../common/interfaces/client/scrapable.interface.js";
import { stringIsAValidUrl } from "../../common/util/urlUtil.js";
import { providedStringPromise } from "../../common/util/promiseUtil.js";

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
