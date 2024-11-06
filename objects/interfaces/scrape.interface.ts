import { Locator } from "playwright-core";
import { ShowDTO } from "../classes/show/show.interface";
import { ComedianDTO } from "../classes/comedian/comedian.interface";

export interface ScrapingOutput {
    show: ShowDTO;
    comedians: ComedianDTO[];
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
