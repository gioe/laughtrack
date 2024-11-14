import { Locator } from "playwright-core";
import { ShowDTO } from "../class/show/show.interface";
import { ComedianDTO } from "../class/comedian/comedian.interface";

export interface ScrapingOutput {
    show: ShowDTO;
    comedians: ComedianDTO[];
}

export interface ClubScraper {
    scrape: () => Promise<ScrapingOutput[]>;
    scrapeShow: (url?: string) => Promise<ScrapingOutput>;
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
