import { HTMLConfigurable } from "./configs.interface.js";

export interface Club extends HTMLConfigurable {
    name: string;
    baseWebsite: string;
    scrapedWebsite: string;
    scraper: string;
}