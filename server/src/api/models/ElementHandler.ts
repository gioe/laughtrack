import { ElementHandle } from "playwright";
import { runTasks } from '../../util/promiseUtil.js';
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";
import {  generateUrlsFromPaths } from "../../util/scrapableUtil.js";

const EMPTY_STYLE_INDICATORS = ['display: none;']

export class ElementHandler {

  getStyle = async (elementHandle: ElementHandle<Element>): Promise<string> => {
    return elementHandle.getAttribute('style').then(href => href ?? "")
  }

  getIsVisible = async (elementHandle?: ElementHandle<Element>): Promise<boolean> => {
    if (elementHandle == undefined) return false
    return this.getStyle(elementHandle)
    .then(style => !EMPTY_STYLE_INDICATORS.includes(style))
  }
  
  getTextContent = async (elementHandle: ElementHandle<Element>):  Promise<string> => {
    return elementHandle.textContent().then(text => text ?? "")
  }
  
  getHref = async (elementHandle: ElementHandle<Element>): Promise<string> => {
    return elementHandle.getAttribute('href').then(href => href ?? "")
  }

  getAllHrefs = async (scrapable: Scrapable, elementHandles: ElementHandle<Element>[]): Promise<string[]> => {
    const tasks = elementHandles.map(elementHandle => this.getHref(elementHandle))
   
    return runTasks(tasks).then((paths: string[]) => generateUrlsFromPaths(scrapable, paths))
  }

  
}