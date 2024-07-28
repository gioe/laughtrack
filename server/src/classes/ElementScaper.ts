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
  }

  getTextValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {
    return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
      .catch(() => { throw new Error(`Error with ${selector} text values`) })
  }

  getTextValueFromSingleElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return object.$eval(selector, (e: Element) => e.textContent ?? "")
      .catch(() => { throw new Error(`Error with ${selector} text value`) })
  }

  getHrefFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? ""))
      .catch(() => { throw new Error(`Error with ${selector} hrefs`) })
  }

  getValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return  object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('value') ?? "") ?? [])
      .catch(() => { throw new Error(`Error with ${selector} values`) })
  }

  getHrefFromSingleElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return object.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
      .catch(() => { throw new Error(`Error with ${selector} href`) })
  }

  getAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<Element[]> => {

    return object.$$eval(selector, (e: Element[]) => e)
      .catch(() => { throw new Error(`Error with ${selector} elements`) })
  }

  getElementHandlers = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<puppeteer.ElementHandle<Element>[]> => {
    return object.$$(selector)
      .catch(() => { throw new Error(`Error with ${selector} element handlers`) })
  }


}