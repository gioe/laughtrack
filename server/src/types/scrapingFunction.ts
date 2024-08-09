import { Comedian } from "../classes/Comedian.js";
import puppeteer from "puppeteer";
import Scrapable from "./scrapable.interface.js";
import Interactable from "./interactable.interface.js";

export type InteractableElement = (Interactable | Interactable[])
export type ScrapableElement = (Scrapable | Scrapable[])

export type GetInteractableFunction = (scrapable: Scrapable) => Promise<any>
export type InteractionFunction = (interactable: InteractableElement, input?: any) => Promise<puppeteer.Page>

export type GetScrapablesFunction = (scrapable: Scrapable) => Promise<ScrapableElement>
export type ScrapingFunction = (scrapable: ScrapableElement) => Promise<Comedian[][]>

export interface ClubScraper {
    firstLoopFunction?: GetInteractableFunction;
    secondLoopFunction?: GetInteractableFunction
    scraperFunction: ScraperFunction;
}

export interface ScraperFunction {
    interactionFunction?: InteractionFunction;
    getScrapableElementsFunction: GetScrapablesFunction;
    scrapeFunction: ScrapingFunction;
}




