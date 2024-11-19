// Database Interface Extensions:

import { PageDataRepository } from "./page";
import { ScraperRepository } from "./scraper";

interface IExtensions {
    scrape: ScraperRepository,
    page: PageDataRepository
}

export {
    ScraperRepository, PageDataRepository
}; export type { IExtensions };

