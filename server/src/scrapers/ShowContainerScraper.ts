import puppeteer from 'puppeteer';
import { runTasks } from '../util/types/promiseUtil.js';
import { ElementScaper } from './ElementScaper.js';
import { LINKS } from '../constants/links.js';
import Scrapable from '../types/scrapable.interface.js';

export class ShowContainerScraper {

  private elementScraper = new ElementScaper();

  getShowDetailPageLinks = async (page: puppeteer.Page,
    showLinkContainerSelector?: string,
    validSignifierSelector?: string,
    showPageLinkSelector?: string, 
  ): Promise<string[]> => {
    
    return this.getShowLinkContainers(page, showLinkContainerSelector)
    .then((elements: puppeteer.ElementHandle<Element>[]) => this.filterInvalidElements(elements, [validSignifierSelector, showPageLinkSelector]))
    .then((validatedValues: (Scrapable | undefined)[]) => validatedValues.filter((value) =>  value !== undefined) as Scrapable[])
    .then((finalElements: Scrapable[]) => this.getAllUrls(finalElements, showPageLinkSelector))
    .then((links: string[]) => links.filter((link: string) => !LINKS.badLinks.includes(link)))
    
  }

  getShowLinkContainers = async (page: puppeteer.Page,
    showLinkContainerSelector?: string
  ): Promise<puppeteer.ElementHandle<Element>[]>  => {
    return this.elementScraper.getElementCount(page, showLinkContainerSelector)
    .then((count: number) => count > 0 ? this.elementScraper.getAllElementsHandlersFrom(page, showLinkContainerSelector) : [])
  }

  filterInvalidElements = async (elements: puppeteer.ElementHandle<Element>[], 
    requiredSelectors: any[]) => {
      const tasks = elements.map((element) => this.elementScraper.validateElement(element, requiredSelectors))
      return runTasks(tasks)
    }

  getAllUrls = async (elements: Scrapable[], 
    showPageLinkSelector?: string): Promise<string[]> => {
      const tasks = elements.map((element) => this.elementScraper.getHrefFrom(element, showPageLinkSelector))      
      return runTasks(tasks)
  }

}