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
    return this.elementScraper.getTextValuesFromAllElements(showComponent, this.allComedianNameSelector())
  }

  scrapeComedians = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    date?: string, 
    url?: string): Promise<Comedian[]> => {
      
    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => {
        return this.getAllComedians(showElementHandler, date, url)
      })

    return runTasks(showScrapingJobs)
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>, date?: string, url?: string): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => {
        return names.length > 0 ? buildComediansFromNames(names, this.comedianHtmlConfig()) : []
      })
      .then((comedians: Comedian[]) => {
        return comedians.length > 0 ? this.addShowToComedianShowList(showComponent, comedians, date, url) : []
      })
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

}
