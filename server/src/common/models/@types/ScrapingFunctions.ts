import playwright, { ElementHandle } from "playwright-core";
import { Show } from "../classes/Show.js";

export type ScrapableElement = (playwright.Page | ElementHandle | ElementHandle[])

export type LoopProviderFunction = (page: playwright.Page) => Promise<any[]>
export type InteractionFunction = (page: playwright.Page, input: any) => Promise<playwright.Page>
export type GetScrapablesFunction = (page: playwright.Page) => Promise<playwright.Page>

export type ScrapingFunction = (page: playwright.Page, input: any) => Promise<Show>
export type ScrapingLoopFunction = (page: playwright.Page) => Promise<Show[]>
