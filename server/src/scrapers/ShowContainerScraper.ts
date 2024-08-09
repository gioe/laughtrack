import puppeteer from 'puppeteer';
import { runTasks } from '../util/types/promiseUtil.js';
import { ElementScaper } from './ElementScaper.js';
import Scrapable from '../types/scrapable.interface.js';
import { validLink } from '../util/types/linkUtil.js';
import { Comedian } from '../classes/Comedian.js';

export class ShowContainerScraper {

  private elementScraper = new ElementScaper();

  getShowDetailPageLinks = async (page: puppeteer.Page,
    showContainerSelector?: string,
    validSignifierSelector?: string,
    showPageLinkSelector?: string, 
  ): Promise<string[]> => {
    return this.getShowLinkContainers(page, showContainerSelector)
    .then((elements: puppeteer.ElementHandle<Element>[]) => this.filterInvalidElements(elements, [validSignifierSelector, showPageLinkSelector]))
    .then((validatedValues: (Scrapable | undefined)[]) => validatedValues.filter((value) =>  value !== undefined) as Scrapable[])
    .then((finalElements: Scrapable[]) => this.getAllUrls(finalElements, showPageLinkSelector))
    .then((links: string[]) => links.filter((link: string) => validLink(link)))
  }

  getShowLinkContainers = async (page: puppeteer.Page,
    showLinkContainerSelector?: string
  ): Promise<puppeteer.ElementHandle<Element>[]>  => {
    return this.elementScraper.getElementCount(page, showLinkContainerSelector)
    .then((count: number) => count > 0 ? this.elementScraper.getAllElementsHandlers(page, showLinkContainerSelector) : [])
  }

  filterInvalidElements = async (elements: puppeteer.ElementHandle<Element>[], 
    requiredSelectors: any[]) => {
      const tasks = elements.map((element) => this.elementScraper.validateElement(element, requiredSelectors))
      return runTasks(tasks)
    }

  getAllUrls = async (elements: Scrapable[], 
    showPageLinkSelector?: string): Promise<string[]> => {
      const tasks = elements.map((element) => this.elementScraper.getHref(element, showPageLinkSelector))      
      return runTasks(tasks)
  }

    
  scrape = async (scrapable: Scrapable): Promise<Comedian[]> => {
    return []
  }

}