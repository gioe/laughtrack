import playwright, { ElementHandle } from "playwright-core";
import { generateValidUrl, generateValidUrls, removeBadWhiteSpace } from "../../../common/util/primatives/stringUtil.js";

export class ScrapableScraper {

  getLink = async (page: playwright.Page, selector: string): Promise<string> => {
    const basePageUrl = page.url()
    return this.getHref(page.locator(selector)).then((href: string) => generateValidUrl(basePageUrl, href));
  }

  getTextContent = async (page: playwright.Page, selector: string): Promise<string[]> => {
    var values: string[] = []
    for (const element of (await page.locator(selector).all())) {
      const value = await this.getText(element)
      values.push(value)
    }
    return values
  }

  getValues = async (page: playwright.Page, selector: string): Promise<string[]> => {
    var values: string[] = []
    for (const element of (await page.locator(selector).all())) {
      const value = await this.getValue(element)
      values.push(value)
    }
    return values
  }

  getLinks = async (page: playwright.Page, selector: string): Promise<string[]> => {
    return this.getAllHrefs(page, selector)
    .then((hrefs: string[]) => {
      const basePageUrl = page.url()
      return generateValidUrls(basePageUrl, hrefs)
    })
  }

  getElementVisibility = async (page: playwright.Page, selector: string): Promise<boolean> => {
    return page.locator(selector).isVisible()
  }
  
  getAllHrefs = async (page: playwright.Page, selector: string): Promise<string[]> => {
    var hrefs: string[] = []
    for (const element of (await page.locator(selector).all())) {
      const href = await this.getHref(element)
      hrefs.push(href)
    }
    return hrefs
  }

  getHref = async (locator: playwright.Locator): Promise<string> => {
    return locator.getAttribute('href').then(href => href ?? "")
  }

  getStyle = async (elementHandle: ElementHandle<Element>): Promise<string> => {
    return elementHandle.getAttribute('style').then(style => style ?? "")
  }

  getValue = async (locator: playwright.Locator): Promise<string> => {
    return locator.getAttribute('value').then(value => value ?? "")
  }

  getText = async (locator: playwright.Locator): Promise<string> => {
    return locator.evaluate(node => node.textContent ?? "").then((value: string) => removeBadWhiteSpace(value))
  }

}