import playwright from 'playwright';
import { Comedian } from '../classes/Comedian.js';

export interface ScraperInterface {
    scrape: (page: playwright.Page) => Promise<Comedian[]>
}