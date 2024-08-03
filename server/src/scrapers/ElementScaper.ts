import puppeteer from 'puppeteer';
import { provideGenericPromiseResponse, runTasks } from '../util/types/promiseUtil.js';
import Scrapable from '../types/scrapable.interface.js';
import { removeBadWhiteSpace } from '../util/types/stringUtil.js';

export class ElementScaper {

  getElementCount = async (object: Scrapable,
    selector?: string): Promise<number> => {
    
      if (selector) {
      return object.$$eval(selector, (e: Element[]) => e.length)
        .then((count: number) => count)
    }
    
    return provideGenericPromiseResponse(0)
  }

  getAllTextContentFrom = async (object: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector) {
      return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
        .then((values: string[]) => values.map((value: string) => removeBadWhiteSpace(value)))
        .catch(() => { throw new Error(`Error with ${selector} text values`) })
    }

    return provideGenericPromiseResponse([])
  }

  getTextContentFrom = async (object: Scrapable,
    selector?: string): Promise<string> => {

    if (selector) {
      return object.$eval(selector, (e: Element) => e.textContent ?? "")
        .then((value: string) => removeBadWhiteSpace(value))
        .catch(() => { throw new Error(`Error with ${selector} text value`) })
    }

    return provideGenericPromiseResponse("")

  }

  getAllHrefsFrom = async (object: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector) {
      return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? ""))
        .then((values: string[]) => values.map((value: string) => removeBadWhiteSpace(value)))
        .catch(() => { throw new Error(`Error with ${selector} hrefs`) })
    }

    return provideGenericPromiseResponse([])
  }

  getAllValuesFrom = async (object: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector) {
      return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('value') ?? "") ?? [])
        .then((values: string[]) => values.map((value: string) => removeBadWhiteSpace(value)))
        .catch(() => { throw new Error(`Error with ${selector} values`) })
    }

    return provideGenericPromiseResponse([])
  }

  getHrefFrom = async (object: Scrapable,
    selector?: string): Promise<string> => {

    if (selector) {
      return object.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
        .then((value: string) => removeBadWhiteSpace(value))
        .catch(() => { throw new Error(`Error with ${selector} href`) })
    }

    return provideGenericPromiseResponse("")
  }

  getAllElementsFrom = async (object: Scrapable,
    selector?: string): Promise<Element[]> => {

    if (selector) {
      return object.$$eval(selector, (e: Element[]) => e)
        .catch(() => { throw new Error(`Error with ${selector} elements`) })
    }

    return provideGenericPromiseResponse([])

  }

  getAllElementsHandlersFrom = async (object: Scrapable,
    selector?: string): Promise<puppeteer.ElementHandle<Element>[]> => {

    if (selector) {
      return object.$$(selector)
        .catch(() => { throw new Error(`Error with ${selector} element handlers`) })
    }

    return provideGenericPromiseResponse([])
  }

  validateElement = async (object: Scrapable,
    requiredSelectors: any[]): Promise<Scrapable | undefined> => {
      
    const tasks = requiredSelectors
      .filter((selector: string) => selector !== "" && selector !== undefined)
      .map(selector => this.getElementCount(object, selector))

    return runTasks(tasks)
      .then((counts: number[]) => counts.filter(count => count > 0).length == tasks.length)
      .then((valid: boolean) => valid ? object : undefined)
  }

}