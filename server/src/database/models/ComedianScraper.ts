import { ScrapableScraper } from "./ScrapableScraper.js";
import { buildComediansFromNames } from "../../util/comedianUtil.js";
import { Comedian } from "../../classes/Comedian.js";
import { ScrapingConfig } from "../../classes/ScrapingConfig.js";
import { ElementCounter } from "./ElementCounter.js";
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();
  private elementCounter = new ElementCounter();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getAllComedianNames = async (scrapable: Scrapable): Promise<Comedian[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : [])
      .then((names: string[]) =>  buildComediansFromNames(names, this.scrapingConfig))
  }

}
