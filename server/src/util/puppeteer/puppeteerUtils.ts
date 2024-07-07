import puppeteer from "puppeteer";


export const getElementCount = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<number> => {
  return object.$$eval(selector, (e: Element[]) => e.length)
}

export const getTextValuesFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<string[]> => {
  return object.$$eval(selector, (e: Element[]) => e.map(e => e.textContent ?? "") ?? [])
}

export const getTextValueFromSingleElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<string> => {
  return object.$eval(selector, (e: Element) => e.textContent ?? "")
}

export const getHrefFromAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<string[]> => {
  return object.$$eval(selector, (e: Element[]) => e.map(e => e.getAttribute('href') ?? "") ?? [])
}

export const getHrefFromSingeElement = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<string> => {
  return object.$eval(selector, (e: Element) => e.getAttribute('href') ?? "")
}

export const getAllElements = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<Element[]> => {
  return object.$$eval(selector, (e: Element[]) => e )
}

export const getElementHandlers = async (object: puppeteer.Page | puppeteer.ElementHandle<Element>, 
  selector: string): Promise<puppeteer.ElementHandle<Element>[]> => {
  return object.$$(selector)
}