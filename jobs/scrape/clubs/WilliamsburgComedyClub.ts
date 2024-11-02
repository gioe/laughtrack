import { Show } from "../../../classes/Show";
import {
    ClubInterface,
    ClubScraper,
    ScrapingOutput,
} from "../../../interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { delay } from "../../../util/promiseUtil";

const LINK = "a.event-card-big-new__image";
const CONTAINER = "div.container.q-py-lg";
const DATE_TIME =
    "div.event-info-col > div.date-formatted > span.q-mr-sm.text-positive";
const SHOW_NAME = "div.event-info-title";
const PRICE =
    "#event-info-right-sticky > div.event-info-right-container > div > div > div";

export class WilliamsburgComedyClub implements ClubScraper {
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
                console.log(`Error scraping Williamburg Comedy Club: ${error}`);
                return [];
            });
    };

    runClubScrapingFunction = async (
        page: playwright.Page,
    ): Promise<ScrapingOutput[]> => {
        await page.locator(CONTAINER).waitFor();

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
            .then(() => delay(2000))
            .then(() => {
                return this.scraper.scrape({
                    dateTimeLocator: page.locator(DATE_TIME),
                    showNameLocator: page.locator(SHOW_NAME),
                    priceLocator: page.locator(PRICE),
                });
            })
            .then((scrapingOutput: any[]) =>
                this.processOutput(scrapingOutput, link),
            );
    };

    processOutput = (output: any[], url: string): ScrapingOutput => {
        const show = new Show({
            lineup: output[0],
            dateTime: new DateTimeContainer(output[1]).asDateObject(),
            ticketLink: generateValidUrl(this.clubData.baseUrl, url),
            name: output[3],
            price: output[4],
            clubId: this.clubData.id,
        });
        return {
            show: show.asCreateShowDTO(),
            comedians: show.asCreateComedianDTOArray(),
        } as ScrapingOutput;
    };
}
