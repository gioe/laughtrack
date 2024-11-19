// Database Interface Extensions:

import { ActionRepository } from "./actions";
import { PageDataRepository } from "./page";
import { ScraperRepository } from "./scraper";

interface IExtensions {
    scrape: ScraperRepository,
    page: PageDataRepository,
    actions: ActionRepository,
}

export {
    ScraperRepository, PageDataRepository,
}; export type { IExtensions };

