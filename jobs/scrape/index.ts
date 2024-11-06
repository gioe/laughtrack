import * as scrapingController from "../../controllers/scrape/index";

export async function runScrapingJob() {
    const args = process.argv.slice(2);
    const idArg = args.find((arg) => arg.startsWith("--arg="));
    const idString = idArg ? idArg.split("=")[1] : "";
    const ids = idString ? idString.split(",") : [];
    const idNumbers = ids.map((id: string) => Number(id));
    console.log("Running scraping job");

    await scrapingController.scrapeClubs(idNumbers);
}

