import { HTMLConfigurable } from "./configs.interface.js";
import puppeteer from 'puppeteer';

export interface Scraper {
    config: HTMLConfigurable;
    scrape: (page: puppeteer.Page) => void;
}
