import playwright from "playwright-core";
import { Comedian } from "../../../common/models/classes/Comedian.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { isEventbritePage } from "../../../common/util/primatives/urlUtil.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  private getComedianNames = async (page: playwright.Page): Promise<string[]> => {
    const nameSelector = isEventbritePage(page) ? this.scrapingConfig.eventbriteComedianNameSelector : this.scrapingConfig.comedianNameSelector
    if (nameSelector) {
      return this.scraper.getTextContent(page, nameSelector)
      .catch((error) => {
        console.error(`Error getting show names: ${error}`)
        return []
      })
    }
    return [];
  }

  scrapeComedians = async (page: playwright.Page): Promise<Comedian[]> => {
    const names = await this.getComedianNames(page);
    if (names.length > 0) {
      return names.map((name: string) => new Comedian(name))
    }
    return []
  }

}
