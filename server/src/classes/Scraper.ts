import puppeteer from 'puppeteer';
import { Logger } from "./Logger.js";

export class Scraper {
  logger: Logger;
  scrapedPage: string;

  constructor(logger: Logger, scrapedPage: string) {
    this.logger = logger;
    this.scrapedPage = scrapedPage;
  }

  getElementCount = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
    selector: string): Promise<number> => {
    return object.$$eval(selector, (e: Element[]) => e.length)
    .then((count: number) => count)
    .catch((error) => {
      this.log(`There was an error getting element count for ${selector}`)
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
            this.log(`There was an error getting all text values for ${selector}`)
            return []
          })
        }
        this.log(`No text values found for ${selector}`)
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
            this.log(`There was an error get text value for ${selector}`)
            return ""
          })
        }
        this.log(`No text value found for ${selector}`)
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
            this.log(`There was an error getting all links for ${selector}`)
            return []
          })
        }
        this.log(`No href values found for ${selector}`)
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
            this.log(`There was an error getting link for ${selector}`)
            return ""
          })
        }
        this.log(`No href value found for ${selector}`)
        return ""
      })
  }
  
  getAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
    selector: string): Promise<Element[]> => {
  
      return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e )
          .catch(() => {
            this.log(`There was an error getting all elements for ${selector}`)
            return []
          })
        }
        this.log(`No elements found for ${selector}`)
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
            this.log(`There was an error getting element handlers for ${selector}`)
            return []
          })
        }
        this.log(`No element handlers found for ${selector}`)
        return []
      })
  
  }
  
  // #region Logger
  log = (input: any) => {
    this.logger.log(this.scrapedPage, input)
  }
  // #endregion

}