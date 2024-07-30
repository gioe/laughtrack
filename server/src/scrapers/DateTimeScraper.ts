import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { normalizeDateTime } from "../util/types/dateTimeUtil.js";
import { Club } from "../classes/Club.js";

export class DateTimeScraper {
  private club: Club;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
  ) {
    this.club = club
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showTimeSelector)
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showDateSelector)
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showDateTimeSelector)
    .then((datetime: string) => normalizeDateTime(datetime, this.club.showConfig))
  }

  combineDateAndTime = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    const dateTask = date ? providedStringPromise(date) : this.getShowDate(showComponent)
    const timeTask = this.getShowTime(showComponent)
    
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {
      if (scrapedValues.length == 0) return ''
      const dateTime = scrapedValues[0] + ' ' + scrapedValues[1]
      return normalizeDateTime(dateTime, this.club.showConfig)
    })

  }

  getShowDateTimeJob = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    return this.club.shouldScrapeShowDatetime ? this.getShowDateTime(showComponent)  : this.combineDateAndTime(showComponent, date)
  }

}
