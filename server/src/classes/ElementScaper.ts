import puppeteer from 'puppeteer';
import { Logger } from "./Logger.js";
import { Club } from './Club.js';

export class ElementScaper {
  club: Club;
  logger: Logger;

  constructor(club: Club, logger: Logger) {
    this.club = club
    this.logger = logger;
  }

  getElementCount = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<number> => {
    return object.$$eval(selector, (e: Element[]) => e.length)
      .then((count: number) => count)
      .catch((error) => {
        this.log(`There was an error getting element count for ${selector} while scraping ${this.club.getName()}`)
        return 0
      })
  }

  getTextValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {
    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
            .catch(() => {
              this.log(`There was an error getting all text values for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        this.log(`No text values found for ${selector} while scraping ${this.club.getName()}`)
        return [];
      })
  }

  getTextValueFromSingleElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$eval(selector, (e: Element) => e.textContent ?? "")
            .catch(() => {
              this.log(`There was an error get text value for ${selector} while scraping ${this.club.getName()}`)
              return ""
            })
        }
        this.log(`No text value found for ${selector} while scraping ${this.club.getName()}`)
        return ""
      })
  }

  getHrefFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? "") ?? [])
            .catch((error) => {
              this.log(`There was an error getting all links for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        this.log(`No href values found for ${selector} while scraping ${this.club.getName()}`)
        return []
      })

  }

  getHrefFromSingeElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
            .catch(() => {
              this.log(`There was an error getting link for ${selector} while scraping ${this.club.getName()}`)
              return ""
            })
        }
        this.log(`No href value found for ${selector} while scraping ${this.club.getName()}`)
        return ""
      })
  }

  getAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<Element[]> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e)
            .catch(() => {
              this.log(`There was an error getting all elements for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        this.log(`No elements found for ${selector} while scraping ${this.club.getName()}`)
        return []
      })
  }

  getElementHandlers = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<puppeteer.ElementHandle<Element>[]> => {
    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$(selector)
            .catch(() => {
              this.log(`There was an error getting element handlers for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        this.log(`No element handlers found for ${selector} while scraping ${this.club.getName()}`)
        return []
      })

  }

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.club.getScrapedPage(), input)
  }
  // #endregion

}