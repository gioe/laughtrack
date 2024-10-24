import { CreateShowDTO } from "./show.interface.js";
import { CreateComedianDTO } from "./comedian.interface.js";
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
  
