import { buildComediansFromNames } from "../../../api/util/comedianUtil.js";
import { ElementCounter } from "../handlers/ElementCounter.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();
  private elementCounter = new ElementCounter();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getAllComedianNames = async (scrapable: Scrapable): Promise<ComedianInterface[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : [])
      .then((names: string[]) =>  buildComediansFromNames(names, this.scrapingConfig))
  }

}
