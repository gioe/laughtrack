import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Club } from "./Club.js";
import { normalizeDateTime } from "../util/types/dateTimeUtil.js";

export class DateTimeScraper {
  club: Club;
  json: any;
  elementScraper: ElementScaper;

  constructor(
    club: Club,
    json: any,
    elementScraper: ElementScaper,
  ) {
    this.club = club
    this.json = json;
    this.elementScraper = elementScraper
  }

  private showHtmlConfig = (): ShowHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.showConfig];
  }

  private shouldScrapeShowDatetime = () => {
    return this.showHtmlConfig().showDateTimeSelector != undefined;
  }

  private showDateTimeSelector = () => {
    return this.showHtmlConfig().showDateTimeSelector ?? "";
  }

  private showTimeSelector = () => {
    return this.showHtmlConfig().showTimeSelector ?? "";
  }

  private showDateSelector = () => {
    return this.showHtmlConfig().showDateSelector ?? "";
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showTimeSelector())
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showDateSelector())
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showDateTimeSelector())
    .then((datetime: string) => normalizeDateTime(datetime, this.showHtmlConfig()))
  }

  combineDateAndTime = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    const dateTask = date ? providedStringPromise(date) : this.getShowDate(showComponent)
    const timeTask = this.getShowTime(showComponent)
    
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {

      if (scrapedValues.length == 0) return ''

      const dateTime = scrapedValues[0] + ' ' + scrapedValues[1]
      
      return normalizeDateTime(dateTime, this.showHtmlConfig())
    })

  }
  
  getShowDateTimeJob = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    if (this.shouldScrapeShowDatetime()) {
     return this.getShowDateTime(showComponent)  
    }
    return this.combineDateAndTime(showComponent, date)
  }


}
