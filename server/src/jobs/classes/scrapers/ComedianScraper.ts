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
export class ComedianScraper {

  private scrapingConfig: ScrapingConfig;
  private club: ClubInterface;
  private scraper = new ScrapableScraper();
  private elementCounter = new ElementCounter();

  constructor(club: ClubInterface, scrapingConfig: ScrapingConfig) {
    this.club = club;
    this.scrapingConfig = scrapingConfig
  }

  getComedianName = async (scrapable: Scrapable): Promise<string> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianNameSelector)
      .then((count: number) => count > 0 ? this.scraper.getTextContent(scrapable, this.scrapingConfig.comedianNameSelector) : "")
  }

  getComedianImage = async (comedianName: string, scrapable: Scrapable): Promise<any> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianImageSelector)
      .then((count: number) => {
        const shouldTakeScreenshot = count > 0 && !this.screenShotExists(comedianName)
        if (shouldTakeScreenshot) {
          const directory = `images/comedians/${removeAllWhiteSpace(comedianName)}`
          const fullPath = directory + `/${this.club.name}.png`
          console.log(fullPath)
          return this.scraper.getScreenshotOfElement(fullPath, scrapable, this.scrapingConfig.comedianImageSelector)
        }
      })
  }

  scrapeComedianContainer = async (element: playwright.ElementHandle<Element>): Promise<ComedianInterface> => {
    const name = await this.getComedianName(element);
    await this.getComedianImage(name, element)
    return new Comedian(name)
  }

  getComedianContainers = async (scrapable: Scrapable): Promise<playwright.ElementHandle<Element>[]> => {
    return this.elementCounter.getElementCount(scrapable, this.scrapingConfig.comedianMetadataContainerSelector)
      .then((count: number) => count > 0 ? this.scraper.getAllElementsHandlers(scrapable, this.scrapingConfig.comedianMetadataContainerSelector) : [])
  }

  getAllComedianData = async (scrapable: Scrapable): Promise<ComedianInterface[]> => {
    return this.getComedianContainers(scrapable)
      .then((elements: playwright.ElementHandle<Element>[]) => {
        const tasks = elements.map((element: playwright.ElementHandle<Element>) => this.scrapeComedianContainer(element))
        return runTasks(tasks)
      })
  }

  screenShotExists = (comedianName: string) => {
    const directory = `images/comedians/${removeAllWhiteSpace(comedianName)}`
    const fullPath = directory + `${this.club}.png`

    if (checkForFileExistence(directory)) {
      if (checkForFileExistence(fullPath)) return true
      return false
    } else {
      makeDirectory(directory)
      return false
    }

  }


}
