import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { buildComediansFromNames } from "../util/types/comedianUtil.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { ShowScraper } from "./ShowScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ComedianHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Show } from "../types/show.interface.js";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";
import { ProvidedScrapingValue } from "../types/providedScrapingValue.interface.js";

export class ComedianScraper {
  private club: Club;
  private json: any;
  private showScraper: ShowScraper;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
    json: any,
    showScraper: ShowScraper
  ) {
    this.club = club;
    this.json = json;
    this.showScraper = showScraper;
  }

  private comedianHtmlConfig = (): ComedianHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.comedianConfig];
  }

  private allComedianNameSelector = () => {
    return this.comedianHtmlConfig().allComedianNameSelector ?? "";
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return this.elementScraper.getElementCount(showComponent, this.allComedianNameSelector())
      .then((count: number) => count > 0 ? this.elementScraper.getTextValuesFromAllElements(showComponent, this.allComedianNameSelector()) : [])
  }

  scrapeComedians = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    providedScrapingValues?: ProvidedScrapingValue
  ): Promise<Comedian[]> => {

    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => this.getAllComedians(showElementHandler, providedScrapingValues))

    return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => this.handleComedianArrays(comedianArrays, providedScrapingValues));
  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, providedScrapingValues?: ProvidedScrapingValue): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => buildComediansFromNames(names, this.comedianHtmlConfig()))
      .then((comedians: Comedian[]) => this.addShowToComedianShowList(showComponent, comedians, providedScrapingValues))
  }

  addShowToComedianShowList = async (showComponent: puppeteer.ElementHandle<Element>,
    comedians: Comedian[],
    providedScrapingValues?: ProvidedScrapingValue
  ): Promise<Comedian[]> => {

    return this.showScraper.scrapeShow(showComponent, providedScrapingValues).then((show: Show) => {
      comedians.forEach((comedian: Comedian) => {
        comedian.addShow(show)
        return comedian
      })
      return comedians
    })
  }

  handleComedianArrays = (comedianArrays: Comedian[][], providedScrapingValues?: ProvidedScrapingValue ) => {
    const urlOrDefault = providedScrapingValues?.ticketUrl ? ` at ${providedScrapingValues.ticketUrl}` : ""
    const dateOrDefault = providedScrapingValues?.date  ? ` on ${providedScrapingValues.date}` : ""

    const flattened = flattenElements(comedianArrays)
    if (flattened.length == 0) console.warn(`Scraping ${this.club.getName()}${urlOrDefault}${dateOrDefault} resuled in no comedians`)
    return flattened;
  }

}
