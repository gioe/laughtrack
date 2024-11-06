import {
    ClubScraper,
    ScrapingOutput,
} from "../../../objects/interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { ClubInterface } from "../../../objects/classes/club/club.interface";
import { Show } from "../../../objects/classes/show/Show";

const LINK =
    "div.col-xs-12.col-sm-3.upcoming-list-description.--btn-container > a";
const DATE_TIME = "ul > li.featured-event-date";
const COMEDIAN_NAME = "p.comedian-name";
const SHOW_NAME = "li.featured-event-title";
const PRICE =
    "div.event-ticket-type.col-sm-10.col-xs-9 > span.ticket-price.original";

export class TheTinyCupboard implements ClubScraper {
    private clubData: ClubInterface;
    private browser: playwright.Browser;
    private pageManager = new PageManager();
    private scraper = new ShowScraper();

    constructor(clubData: ClubInterface, browser: playwright.Browser) {
        this.clubData = clubData;
        this.browser = browser;
    }

    scrape = async (): Promise<ScrapingOutput[]> => {
        return this.browser
            .newPage()
            .then((page: playwright.Page) =>
                this.pageManager.navigateToUrl(
                    page,
                    this.clubData.scrapingPageUrl,
                ),
            )
            .then((page: playwright.Page) => this.runClubScrapingFunction(page))
            .catch((error) => {
                console.log(`Error scraping The Tiny Cupboard: ${error}`);
                return [];
            });
    };

    runClubScrapingFunction = async (
        page: playwright.Page,
    ): Promise<ScrapingOutput[]> => {
        const linksLocator = page.locator(LINK);
        return this.pageManager
            .getAllLinksOnPage(page.url(), linksLocator)
            .then((links: string[]) => this.runScrapingLoop(page, links));
    };

    runScrapingLoop = async (
        page: playwright.Page,
        links: string[],
    ): Promise<ScrapingOutput[]> => {
        const scrapedOutput: ScrapingOutput[] = [];

        for (let index = 0; index < links.length - 1; index++) {
            const input = links[index];
            const output = await this.navigateToUrlAndScrape(page, input);
            scrapedOutput.push(output);
        }

        await this.browser.close();
        return scrapedOutput;
    };

    navigateToUrlAndScrape = async (
        page: playwright.Page,
        link: string,
    ): Promise<ScrapingOutput> => {
        return this.pageManager
            .navigateToUrl(page, link)
            .then((page) => {
                return this.scraper.scrape({
                    comedianNameLocator: page.locator(COMEDIAN_NAME),
                    dateTimeLocator: page.locator(DATE_TIME),
                    showNameLocator: page.locator(SHOW_NAME),
                    priceLocator: page.locator(PRICE),
                });
            })
            .then((scrapingOutput: any[]) =>
                this.processOutput(scrapingOutput, link),
            );
    };

    processOutput = (output: any[], link: string): ScrapingOutput => {
        const show = new Show({
            lineup: output[0],
            date_time: new DateTimeContainer(output[1]).asDateObject(),
            ticket_link: generateValidUrl(this.clubData.baseUrl, link),
            name: output[3],
            price: output[4],
            club_id: this.clubData.id,
        });
        return {
            show: show.asShowDTO(),
            comedians: show.asComedianDTOArray(),
        } as ScrapingOutput;
    };
}
