import playwright from "playwright-core";
import { Scrapable } from "../../common/interfaces/client/scrape.interface.js";
import { Comedian } from "../../common/models/Comedian.js";
import { ScrapingConfig } from "../../common/models/ScrapingConfig.js";
import { runTasks } from "../../common/util/promiseUtil.js";
import { buildComediansFromNames } from "../../common/util/comedianUtil.js";
import { ElementCounter } from "./handlers/ElementCounter.js";
import { ScrapableScraper } from "./ScrapableScraper.js";

export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();
  private elementCounter = new ElementCounter();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getAllComedianData = async (scrapable: Scrapable): Promise<Comedian[]> => {
    return this.getComedianContainers(scrapable)
      .then((elements: playwright.ElementHandle<Element>[]) => elements.length > 0 ? this.scrapeAllContainers(elements) : this.scrapeNames(scrapable))
  }

  getComedianName = async (scrapable: Scrapable): Promise<string> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : "")
  }

  getComedianContainers = async (scrapable: Scrapable): Promise<playwright.ElementHandle<Element>[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianMetadataContainerSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllElementsHandlers(scrapable, this.scrapingConfig.comedianMetadataContainerSelector) : [])
  }

  scrapeComedianContainer = async (element: playwright.ElementHandle<Element>): Promise<Comedian> => {
    const name = await this.getComedianName(element);
    return new Comedian(name)
  }

  scrapeAllContainers = async (elements: playwright.ElementHandle<Element>[]) => {
    const tasks = elements.map((element: playwright.ElementHandle<Element>) => this.scrapeComedianContainer(element))
    return runTasks(tasks)
  }

  scrapeNames = async (scrapable: Scrapable): Promise<Comedian[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : [])
      .then((names: string[]) => buildComediansFromNames(names, this.scrapingConfig))
  }

}
