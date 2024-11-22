import {
    ClubScraper,
    ScrapingOutput,
} from "../../../objects/interface";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { PageScraper } from "../scrapers/PageScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { Show } from "../../../objects/class/show/Show";
import { ClubInterface } from "../../../objects/class/club/club.interface";
import { ShowScraper } from "../../../objects/interface/scrape.interface";
import { runTasks } from "../../../util/promiseUtil";

const SHOW_CONTAINER = "listitem";
const DATE_TIME = "p.b-venue";
const SHOW_NAME = "div.event-name.show";
const TICKET_LINK = "a.day-card.w-inline-block";
const SEPARATOR = ",";

export class StMarksComedyClub implements ClubScraper, ShowScraper {
    private clubData: ClubInterface;
    private browser: playwright.Browser;
    private pageManager = new PageManager();
    private scraper = new PageScraper();

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
                )
            )
            .then((page: playwright.Page) => this.runClubScrapingFunction(page))
            .catch((error) => {
                console.log(`Error scraping The Stand: ${error}`);
                return [];
            });
    };


    scrapeShow = async (): Promise<ScrapingOutput> => {
        throw new Error("Can't scrape pages from this club")
    }

    runClubScrapingFunction = async (page: playwright.Page): Promise<ScrapingOutput[]> => {
        return page.getByRole(SHOW_CONTAINER).all()
            .then((containers: playwright.Locator[]) => {
                console.log(`Found ${containers.length} containers`)
                const tasks = containers.map((value: playwright.Locator) =>
                    this.scrapeContainer(value),
                );
                return runTasks(tasks);
            })
            .then((output: ScrapingOutput[]) => {
                this.browser.close();
                return output;
            });
    };

    scrapeContainer = async (container: playwright.Locator): Promise<ScrapingOutput> => {
        return this.scraper
            .scrape({
                dateTimeLocator: container.locator(DATE_TIME),
                ticketLinkLocator: container.locator(TICKET_LINK),
                showNameLocator: container.locator(SHOW_NAME),
            })
            .then((scrapingOutput: unknown[]) =>
                this.processOutput(scrapingOutput),
            );
    };

    processOutput = async (output: unknown[]): Promise<ScrapingOutput> => {
        console.log(output)
        const show = new Show({
            date: new DateTimeContainer(
                output[1] as string[],
                SEPARATOR
            ).asDateObject(),
            ticket: {
                link: generateValidUrl(this.clubData.website, output[2] as string),
                price: 0
            },
            name: output[3] as string,
            club_id: this.clubData.id,
            last_scraped_date: new Date(),
        });
        return {
            show: show.asShowDTO(),
            comedians: show.asComedianDTOArray(),
        } as ScrapingOutput;
    };
}
