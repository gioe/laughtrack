import puppeteer from "puppeteer";
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

  constructor(
    club: Club,
    json: any,
    elementScraper: ElementScaper,
    showScraper: ShowScraper
  ) {
    this.club = club;
    this.json = json;
    this.elementScraper = elementScraper
    this.showScraper = showScraper
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
    date?: string,
    url?: string): Promise<Comedian[]> => {

    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => this.getAllComedians(showElementHandler, date, url))

    return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => this.handleComedianArrays(comedianArrays, date, url));
  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, date?: string, url?: string): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => buildComediansFromNames(names, this.comedianHtmlConfig()))
      .then((comedians: Comedian[]) => this.addShowToComedianShowList(showComponent, comedians, date, url))
  }

  addShowToComedianShowList = async (showComponent: puppeteer.ElementHandle<Element>,
    comedians: Comedian[],
    date?: string,
    url?: string): Promise<Comedian[]> => {

    return this.showScraper.scrapeShow(showComponent, date, url).then((show: Show) => {
      comedians.forEach((comedian: Comedian) => {
        comedian.addShow(show)
        return comedian
      })
      return comedians
    })
  }

  handleComedianArrays = (comedianArrays: Comedian[][], date?: string, url?: string, ) => {
    const urlOrDefault = url ?? ""
    const dateOrDefault = date ? ` on ${date}` : ""

    const flattened = flattenElements(comedianArrays)
    if (flattened.length == 0) console.warn(`Scraping ${urlOrDefault}${dateOrDefault} resuled in no comedians`)
    return flattened;
  }

}
