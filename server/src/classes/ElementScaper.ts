import puppeteer from 'puppeteer';
import { Club } from './Club.js';

export class ElementScaper {
  club: Club;

  constructor(club: Club) {
    this.club = club
  }

  getElementCount = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<number> => {
    return object.$$eval(selector, (e: Element[]) => e.length)
      .then((count: number) => count)
      .catch(() => 0)
  }

  getTextValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {
    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
            .catch(() => {
              console.log(`There was an error getting all text values for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
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
              console.log(`There was an error get text value for ${selector} while scraping ${this.club.getName()}`)
              return ""
            })
        }
        return ""
      })
  }

  getHrefFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => {
            return e.map(e => e.getAttribute('href') ?? "")
          })
            .catch(() => {
              console.log(`There was an error getting all links for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        return []
      })

  }

  getValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return this.getElementCount(object, selector)
      .then((count: number) => {
        if (count > 0) {
          return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('value') ?? "") ?? [])
            .catch((error) => {
              console.log(`There was an error getting all links for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
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
              console.log(`There was an error getting link for ${selector} while scraping ${this.club.getName()}`)
              return ""
            })
        }
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
              console.log(`There was an error getting all elements for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
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
              console.log(`There was an error getting element handlers for ${selector} while scraping ${this.club.getName()}`)
              return []
            })
        }
        return []
      })

  }


}