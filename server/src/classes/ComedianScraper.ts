import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Comedian } from './Comedian.js';
import { ElementScaper } from "./ElementScaper.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { normalizeNameString } from "../util/types/comedianUtil.js";
import { Club } from "./Club.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { ShowScraper } from "./ShowScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ComedianHTMLConfiguration } from "../types/htmlconfigurable.interface.js";

export class ComedianScraper {
  club: Club;
  json: any;
  elementScraper: ElementScaper;
  showScraper: ShowScraper;
  logger: Logger;

  constructor(
    club: Club,
    json: any,
    elementScraper: ElementScaper,
    showScraper: ShowScraper,
    logger: Logger,
  ) {
    this.club = club;
    this.json = json;
    this.elementScraper = elementScraper
    this.showScraper = showScraper
    this.logger = logger;
  }

  private getComedianHtmlConfig = (): ComedianHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.comedianConfig];
  }

  private allComedianNameSelector = () => {
    return this.getComedianHtmlConfig().allComedianNameSelector ?? "";
  }

  scrapeComedians = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    club: Club,
    date?: string): Promise<Comedian[]> => {

    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => {
        return this.getAllComedians(showElementHandler, club, date)
      })

    return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))

  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, club: Club, date?: string): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => this.buildComedianFromScrapedElements(names))
      .then((comedians: Comedian[]) => {
        this.log(`Scraped ${comedians.length} comedians from this show`)
        return this.showScraper.scrapeShowForComedians(showComponent, comedians, club, date)
      })
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return this.elementScraper.getTextValuesFromAllElements(showComponent, this.allComedianNameSelector())
  }

  buildComedianFromScrapedElements = (comedianNames: string[]): Comedian[] => {
    return comedianNames
      .map((comedianName: string) => normalizeNameString(comedianName, this.getComedianHtmlConfig()))
      .flatMap((names: string[]) => names.map((name: string) => new Comedian(name)))
  }

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.club.getScrapedPage(), input)
  }
  // #endregion

}
