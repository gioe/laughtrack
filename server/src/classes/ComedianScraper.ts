import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Comedian } from './Comedian.js';
import { TextConfigurable } from '../types/textConfigurable.interface.js';
import { Scraper } from "./Scraper.js";
import { ComedianHTMLConfiguration, HTMLConfigurable } from "../types/htmlconfigurable.interface.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { cleanNameString } from "../util/types/comedianUtil.js";
import { Club } from "./Club.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { ShowScraper } from "./ShowScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";

export class ComedianScraper {
  logger: Logger;
  textConfig: TextConfigurable;
  comedianConfig: ComedianHTMLConfiguration;
  showScraper: ShowScraper;
  scraper: Scraper;

  constructor(logger: Logger, 
    json: any) {
    this.logger = logger;
    this.comedianConfig = json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.comedianConfig];
    this.textConfig = json[SCRAPER_KEYS.textConfig]
    this.showScraper = new ShowScraper(logger, json)
    this.scraper = new Scraper(logger, json[SCRAPER_KEYS.scrapedPage])
  }

  private allComedianNameSelector = () => {
    return this.comedianConfig.allComedianNameSelector ?? "";
  }
  
  scrapeComedians = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    club: Club,
    date?: string): Promise<Comedian[]> => {

      // The showElementHandlers are all the show divs on a given page. 
      // We generate a single task to scrape the comedians from each div.
      const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => {
        return this.getAllComedians(showElementHandler, club, date)
      })

      return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
    }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, club: Club, date?: string): Promise<Comedian[]> => {
    // To determine the list of comedians, we first extract all of the names, which are our best signal for 
    // comedian existence.
    return this.getAllComedianNames(showComponent)
    .then((names: string[]) => this.buildComedianFromScrapedElements(names))
    .then((comedians: Comedian[]) => this.showScraper.scrapeShowForComedians(showComponent, comedians, club, date))
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return this.scraper.getTextValuesFromAllElements(showComponent, this.allComedianNameSelector())
  }

  buildComedianFromScrapedElements = (comedianNames: string[]): Comedian[] => {
    return comedianNames
      .map((comedianName: string) => {
        this.log(comedianName)
        return cleanNameString(comedianName, this.textConfig)
      })
      .map((actualName: string) => this.buildComedian(actualName))
  }

  buildComedian = (name: string): Comedian => {
    const comedian = new Comedian(name, "");
    return comedian
  }

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.scraper.scrapedPage, input)
  }
  // #endregion

}
