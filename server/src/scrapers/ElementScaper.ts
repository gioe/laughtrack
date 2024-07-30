import puppeteer from 'puppeteer';
import { runTasks } from '../util/types/promiseUtil.js';

export class ElementScaper {

  getElementCount = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<number> => {
    return object.$$eval(selector, (e: Element[]) => e.length)
      .then((count: number) => count)
  }

  getAllTextContentFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {
    return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
      .catch(() => { throw new Error(`Error with ${selector} text values`) })
  }

  getTextContentFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return object.$eval(selector, (e: Element) => e.textContent ?? "")
      .catch(() => { throw new Error(`Error with ${selector} text value`) })
  }

  getAllHrefsFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? ""))
      .catch(() => { throw new Error(`Error with ${selector} hrefs`) })
  }

  getAllValuesFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string[]> => {

    return  object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('value') ?? "") ?? [])
      .catch(() => { throw new Error(`Error with ${selector} values`) })
  }

  getHrefFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<string> => {

    return object.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
      .catch(() => { throw new Error(`Error with ${selector} href`) })
  }

  getAllElementsFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<Element[]> => {

    return object.$$eval(selector, (e: Element[]) => e)
      .catch(() => { throw new Error(`Error with ${selector} elements`) })
  }

  getAllElementsHandlersFrom = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>,
    selector: string): Promise<puppeteer.ElementHandle<Element>[]> => {
    return object.$$(selector)
      .catch(() => { throw new Error(`Error with ${selector} element handlers`) })
  }

  validateElements = async (object: puppeteer.ElementHandle<Element>,
    requiredSelectors: string[]): Promise<puppeteer.ElementHandle<Element> | undefined> => {
      const tasks = requiredSelectors.map(selector => this.getElementCount(object, selector))
    
      return runTasks(tasks)
      .then((counts: number[]) => counts.filter(count => count > 0).length == tasks.length)
      .then((valid: boolean) => valid ? object : undefined)
  }

}