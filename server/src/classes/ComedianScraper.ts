import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Comedian } from './Comedian.js';
import { ElementScaper } from "./ElementScaper.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { buildComediansFromNames } from "../util/types/comedianUtil.js";
import { Club } from "./Club.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { ShowScraper } from "./ShowScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ComedianHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Show } from "../types/show.interface.js";

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

  private comedianHtmlConfig = (): ComedianHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.comedianConfig];
  }

  private allComedianNameSelector = () => {
    return this.comedianHtmlConfig().allComedianNameSelector ?? "";
  }

  scrapeComedians = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    date?: string): Promise<Comedian[]> => {

    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => {
        return this.getAllComedians(showElementHandler, date)
      })

    return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, date?: string): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => buildComediansFromNames(names, this.comedianHtmlConfig()))
      .then((comedians: Comedian[]) =>  this.addShowToComedianShowList(showComponent, comedians, date))
  }

  addShowToComedianShowList = async (showComponent: puppeteer.ElementHandle<Element>, comedians: Comedian[], date?: string): Promise<Comedian[]> => {
    return this.showScraper.scrapeShow(showComponent, date).then((show: Show) => {
      comedians.forEach((comedian: Comedian) => {
        comedian.addShow(show)
        return comedian
      })
      return comedians
    })
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return this.elementScraper.getTextValuesFromAllElements(showComponent, this.allComedianNameSelector())
  }

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.club.getScrapedPage(), input)
  }
  // #endregion

}
