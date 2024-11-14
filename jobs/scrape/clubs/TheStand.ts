import {
    ClubScraper,
    ScrapingOutput,
} from "../../../objects/interface";
import { PageManager } from "../handlers/PageManager";
import playwright, { Browser, Locator, Page } from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { runTasks } from "../../../util/promiseUtil";
import { ClubInterface } from "../../../objects/class/club/club.interface";
import { Show } from "../../../objects/class/show/Show";
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface";

const MORE = "div.row.moreitems.dark-links.my-5 > div > div > a";
const SHOW_CONTAINER = "div.row.show_row";
const DATE_TIME = "span.show_date";
const COMEDIAN_NAME = "div.col-4.col-md-3.col-xl-2.lineup-item";
const SHOW_NAME = "h2.showtitle";
const TICKET_LINK = "div.d-grid.gap-2 > a";
const PRICE = "div.price";
const SEPARATOR = ",";
const MODAL = "div.modal-content.pop-up-bg-tan"


export class TheStand implements ClubScraper {
    private clubData: ClubInterface;
    private browser: Browser;
    private pageManager = new PageManager();
    private scraper = new ShowScraper();

    constructor(clubData: ClubInterface, browser: playwright.Browser) {
        this.clubData = clubData;
        this.browser = browser;
    }

    scrape = async (): Promise<ScrapingOutput[]> => {
        return this.browser
            .newPage()
            .then((page: Page) =>
                this.pageManager.navigateToUrl(
                    page,
                    this.clubData.scrapingPageUrl,
                ),
            )
            .then((page: Page) => this.closeBlockingModal(page))
            .then((page: Page) => this.runClubScrapingFunction(page))
            .catch((error) => {
                console.log(`Error scraping The Stand: ${error}`);
                return [];
            });
    };


    scrapeShow = async (): Promise<ScrapingOutput> => {
        throw new Error("Can't scrape pages from this club")
    }

    closeBlockingModal = async (page: Page): Promise<Page> => {
        const modalLocator = page.locator(MODAL);
        const closeButtonLocator = modalLocator.getByRole('button', { name: 'X' })
        return closeButtonLocator.click().then(() => page)
    }

    runClubScrapingFunction = async (page: Page): Promise<ScrapingOutput[]> => {
        const moreLocator = page.locator(MORE);
        return this.pageManager
            .expandPage(page, moreLocator)
            .then((page) => page.locator(SHOW_CONTAINER).all())
            .then((containers: playwright.Locator[]) => {
                const tasks = containers.map((value: Locator) =>
                    this.scrapeContainer(value),
                );
                return runTasks(tasks);
            })
            .then((output: ScrapingOutput[]) => {
                this.browser.close();
                return output;
            });
    };

    scrapeContainer = async (container: Locator): Promise<ScrapingOutput> => {
        return this.scraper
            .scrape({
                comedianNameLocator: container.locator(COMEDIAN_NAME),
                dateTimeLocator: container.locator(DATE_TIME),
                ticketLinkLocator: container.locator(TICKET_LINK),
                showNameLocator: container.locator(SHOW_NAME),
                priceLocator: container.locator(PRICE),
            })
            .then((scrapingOutput: unknown[]) =>
                this.processOutput(scrapingOutput),
            );
    };

    processOutput = async (output: unknown[]): Promise<ScrapingOutput> => {
        const show = new Show({
            lineup: output[0] as ComedianDTO[],
            date: new DateTimeContainer(
                output[1] as string[],
                SEPARATOR,
            ).asDateObject(),
            ticket: {
                link: generateValidUrl(this.clubData.website, output[2] as string),
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
