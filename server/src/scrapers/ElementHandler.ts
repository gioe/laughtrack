import { ElementHandle } from "playwright";
import { runTasks } from '../util/types/promiseUtil.js';
import { Scrapable } from "../types/scrapable.interface.js";
import { generateCompleteUrl } from "../util/types/scrapableUtil.js";

export class ElementHandler {

  getTextContent = async (elementHandle: ElementHandle<Element>): Promise<string> => {
    return elementHandle.evaluate(element => element.textContent ?? "")
  }

  getAllHrefs = async (scrapable: Scrapable, elementHandles: ElementHandle<Element>[]): Promise<string[]> => {
    const tasks = elementHandles.map(elementHandle => this.getHref(elementHandle))
    return runTasks(tasks).then((paths: string[]) =>  paths.map(path => generateCompleteUrl(scrapable, path)))
  }

  getHref = async (elementHandle: ElementHandle<Element>): Promise<string> => {
    return elementHandle.evaluate(element => element.getAttribute('href') ?? "")
  }

}