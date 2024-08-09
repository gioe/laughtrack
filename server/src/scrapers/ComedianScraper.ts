import Scrapable from "../types/scrapable.interface.js";
import { ElementScaper } from "./ElementScaper.js";
import { buildComediansFromNames } from "../util/types/comedianUtil.js";
import { Comedian } from "../classes/Comedian.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private elementScraper = new ElementScaper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getAllComedianNames = async (showComponent: Scrapable): Promise<Comedian[]> => {
    return this.elementScraper.getElementCount(showComponent, this.scrapingConfig.nameSelector)
      .then((count: number) => count > 0 ? this.elementScraper.getAllTextContent(showComponent, this.scrapingConfig.nameSelector) : [])
      .then((names: string[]) =>  buildComediansFromNames(names, this.scrapingConfig))
  }

}
