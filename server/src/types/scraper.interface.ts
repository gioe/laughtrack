import puppeteer from 'puppeteer';
import { Comedian } from '../classes/Comedian.js';

export interface ScraperInterface {
    scrapedPage: string;
    scrape: (page: puppeteer.Page) => Promise<Comedian[]>
}