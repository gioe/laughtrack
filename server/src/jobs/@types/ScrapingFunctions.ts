import playwright, { ElementHandle } from "playwright-core";
import { Scrapable } from "../../common/interfaces/scrapable.interface.js";
import { ShowInterface } from "../../common/interfaces/show.interface.js";

export type ScrapableElement = (playwright.Page | ElementHandle | ElementHandle[])

export type LoopProviderFunction = (page: playwright.Page) => Promise<any[]>
export type InteractionFunction = (page: playwright.Page, input: any) => Promise<playwright.Page>
export type GetScrapablesFunction = (scrapable: Scrapable) => Promise<Scrapable>

export type ScrapingFunction = (scrapable: Scrapable, input: any) => Promise<ShowInterface[]>
export type ScrapingLoopFunction = (scrapable: Scrapable) => Promise<ShowInterface[]>
