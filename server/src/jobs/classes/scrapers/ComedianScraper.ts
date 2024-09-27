import playwright from "playwright-core";
import { ElementCounter } from "../handlers/ElementCounter.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { runTasks } from "../../../common/util/promiseUtil.js";
import { Comedian } from "../models/Comedian.js";
import { ClubInterface } from "../../../common/interfaces/club.interface.js";
import { checkForFileExistence, makeDirectory } from "../../../common/util/fileSystemUtil.js";
import { removeAllWhiteSpace } from "../../util/stringUtil.js";
import { buildComediansFromNames } from "../../util/comedianUtil.js";
export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private club: ClubInterface;
  private scraper = new ScrapableScraper();
  private elementCounter = new ElementCounter();

  constructor(club: ClubInterface, scrapingConfig: ScrapingConfig) {
    this.club = club;
    this.scrapingConfig = scrapingConfig
  }

  getAllComedianData = async (scrapable: Scrapable): Promise<ComedianInterface[]> => {
    return this.getComedianContainers(scrapable)
      .then((elements: playwright.ElementHandle<Element>[]) => elements.length > 0 ? this.scrapeAllContainers(elements) : this.scrapeNames(scrapable))
  }

  getComedianName = async (scrapable: Scrapable): Promise<string> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : "")
  }

  getComedianImage = async (comedianName: string, scrapable: Scrapable): Promise<any> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianImageSelector)
      .then((count: number) => {
        const fullPath = `images/comedians/${comedianName}.png`
        const shouldTakeScreenshot = count > 0 && !checkForFileExistence(fullPath)
        if (shouldTakeScreenshot) {
          return this.scraper.getScreenshotOfElement(fullPath, scrapable, this.scrapingConfig.comedianImageSelector)
        }
      })
  }

  getComedianContainers = async (scrapable: Scrapable): Promise<playwright.ElementHandle<Element>[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianMetadataContainerSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllElementsHandlers(scrapable, this.scrapingConfig.comedianMetadataContainerSelector) : [])
  }

  scrapeComedianContainer = async (element: playwright.ElementHandle<Element>): Promise<ComedianInterface> => {
    const name = await this.getComedianName(element);
    await this.getComedianImage(name, element)
    return new Comedian(name)
  }

  scrapeAllContainers = async (elements: playwright.ElementHandle<Element>[]) => {
    const tasks = elements.map((element: playwright.ElementHandle<Element>) => this.scrapeComedianContainer(element))
    return runTasks(tasks)
  }

  scrapeNames = async (scrapable: Scrapable): Promise<ComedianInterface[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : [])
      .then((names: string[]) => buildComediansFromNames(names, this.scrapingConfig))
  }

}
