import puppeteer from 'puppeteer';

export interface Scraper {
    scrape: (page: puppeteer.Page) => void;
}