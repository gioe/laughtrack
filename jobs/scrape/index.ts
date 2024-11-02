import * as scrapingController from "../../controllers/scrape/index";
import { writeLogToFile } from "../../util/logUtil";

async function runScrapingJob() {
    const args = process.argv.slice(2);
    const idArg = args.find((arg) => arg.startsWith("--arg="));
    const idString = idArg ? idArg.split("=")[1] : "";
    const ids = idString ? idString.split(",") : [];
    const idNumbers = ids.map((id: string) => Number(id));
    writeLogToFile("Running scraping job");
    await scrapingController.scrapeClubs(idNumbers);
}

runScrapingJob();
