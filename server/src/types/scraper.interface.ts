import puppeteer from 'puppeteer';
import { Comedian } from '../classes/Comedian.js';

export interface ScraperInterface {
    baseWebsite: string;
    scrape: (page: puppeteer.Page) => Promise<Comedian[]>
}