import playwright from "playwright-core";
import { ElementHandler } from "../handlers/ElementHandler.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { provideGenericPromiseResponse } from "../../../common/util/promiseUtil.js";

export class ScrapableScraper {

  private elementHandler = new ElementHandler();
  

  getAllTextContent = async (scrapable: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector) {
      return scrapable.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
        .catch(() => { console.warn(`Error with ${selector} text values`) })
    }

    return provideGenericPromiseResponse([])
  }

  getTextContent = async (scrapable: Scrapable,
    selector?: string): Promise<string> => {

    if (selector) {
      return scrapable.$eval(selector, (e: Element) => e.textContent ?? "")
        .catch(() => { console.warn(`Error with ${selector} text value`) })
    }

    return provideGenericPromiseResponse("")

  }

  getAllHrefs = async (scrapable: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector) {
      return scrapable.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? ""))
        .catch(() => { console.warn(`Error with ${selector} hrefs`) })
    }

    return provideGenericPromiseResponse([])
  }

  getAllValues = async (scrapable?: Scrapable,
    selector?: string): Promise<string[]> => {

    if (selector && scrapable) {
        return scrapable.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('value') ?? "") ?? [])
        .catch(() => { console.warn(`Error with ${selector} values`) })
    }

    return provideGenericPromiseResponse([])
  }

  getHref = async (scrapable?: Scrapable,
    selector?: string): Promise<string> => {

    if (selector && scrapable) {
        return scrapable.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
        .catch(() => { console.warn(`Error with ${selector} href`) })
    }

    return provideGenericPromiseResponse("")
  }

  getAllElements = async (scrapable?: Scrapable,
    selector?: string): Promise<Element[]> => {

    if (selector && scrapable) {
        return scrapable.$$eval(selector, (e: Element[]) => e)
        .catch(() => { console.warn(`Error with ${selector} elements`) })
    }
    return provideGenericPromiseResponse([])

  }

  getAllElementsHandlers = async (scrapable?: Scrapable,
    selector?: string): Promise<playwright.ElementHandle<Element>[]> => {
    
    if (selector && scrapable) {
      return scrapable.$$(selector)
        .catch(() => { 
          console.warn(`Error with ${selector} element handlers`)
          return []
         })
    }

    return provideGenericPromiseResponse([])
  }

  getElementVisibility = async (scrapable?: Scrapable,
    selector?: string): Promise<boolean> => {

    if (selector && scrapable) {
      return scrapable.$$(selector)
      .then(elementHandles => this.elementHandler.getIsVisible(elementHandles[0]))
      .catch((error) => {
        console.warn(error)
        return true
      })
    }
    return provideGenericPromiseResponse(false)
  }

  getScreenshotOfElement = async (
    fileName: string,
    scrapable?: Scrapable,
    selector?: string) => {

    if (selector && scrapable) {
      const element = await scrapable.$(selector)
      if (element == null) return
      return element.screenshot({ path: fileName });
  }

}}