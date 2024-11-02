import { CreateComedianDTO, CreateShowDTO } from "./";
import { Locator } from "playwright-core";

export interface ScrapingOutput {
    show: CreateShowDTO;
    comedians: CreateComedianDTO[];
}

export interface ClubScraper {
    scrape: () => Promise<ScrapingOutput[]>;
}

export interface ScrapingArgs {
    comedianNameLocator?: Locator;
    dateTimeLocator: Locator;
    ticketLinkLocator?: Locator;
    showNameLocator: Locator;
    priceLocator?: Locator;
}

export interface Scrapable {
    scrapingPageUrl: string;
}
