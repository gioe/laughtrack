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
import { ComedianDTO } from "../../../objects/classes/comedian/comedian.interface";

const LINK =
    "div.col-xs-12.col-sm-6.col-lg-7.upcoming-list-description.calendar-upcoming-list-description > a.btn.btn-default";
const MORE = "#--load-more-shows";
const DATE_TIME = "div.mobile-event-header.header.visible-xs";
const COMEDIAN_NAME = "p.comedian-name > a";
const SHOW_NAME = "span.date-div";
const PRICE = "div.event-ticket-type > span.ticket-price.original";
const TICKET_LINK = "span.date-div";
const SEPARATOR = " - ";

export class NewYorkComedyClub implements ClubScraper {
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
                console.log(`Error scraping New York Comedy Club: ${error}`);
                return [];
            });
    };


    scrapeShow = async (url: string): Promise<ScrapingOutput> => {
        return this.browser
            .newPage()
            .then((page: playwright.Page) =>
                this.navigateToUrlAndScrape(page, url)
            )
    }

    runClubScrapingFunction = async (
        page: playwright.Page,
    ): Promise<ScrapingOutput[]> => {
        const moreLocator = page.locator(MORE);
        return this.pageManager
            .expandPage(page, moreLocator)
            .then((page) => {
                const linksLocator = page.locator(LINK);
                return this.pageManager.getAllLinksOnPage(
                    page.url(),
                    linksLocator,
                );
            })
            .then((links: string[]) => this.runScrapingLoop(page, links));
    };

    runScrapingLoop = async (
        page: playwright.Page,
        links: string[],
    ): Promise<ScrapingOutput[]> => {
        const scrapingOutput: ScrapingOutput[] = [];

        for (let index = 0; index < links.length - 1; index++) {
            const input = links[index];
            const output = await this.navigateToUrlAndScrape(page, input);
            scrapingOutput.push(output);
        }

        await this.browser.close();
        return scrapingOutput;
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
                    ticketLinkLocator: page.locator(TICKET_LINK),
                    showNameLocator: page.locator(SHOW_NAME),
                    priceLocator: page.locator(PRICE),
                });
            })
            .then((scrapingOutput: unknown[]) =>
                this.processOutput(scrapingOutput, link),
            );
    };

    processOutput = (output: unknown[], link: string): ScrapingOutput => {
        const show = new Show({
            lineup: output[0] as ComedianDTO[],
            date_time: new DateTimeContainer(
                output[1] as string[],
                SEPARATOR,
            ).asDateObject(),
            ticket: {
                link: generateValidUrl(this.clubData.baseUrl, link),
                price: output[4] as number
            },
            name: output[3] as string,
            club_id: this.clubData.id,
        });
        return {
            show: show.asShowDTO(),
            comedians: show.asComedianDTOArray(),
        } as ScrapingOutput;
    };
}
