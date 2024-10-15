import playwright from "playwright-core";
import { Comedian } from "../../../common/models/classes/Comedian.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  private getComedianNames = async (page: playwright.Page): Promise<string[]> => {
    return this.scraper.getTextContent(page, this.scrapingConfig.comedianNameSelector)
  }

  scrapeComedians = async (page: playwright.Page): Promise<Comedian[]> => {
    const names = await this.getComedianNames(page);
    return names.map((name: string) => new Comedian(name))
  }

}
