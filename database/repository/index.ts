// Database Interface Extensions:

import { ActionRepository } from "./actions";
import { PageDataRepository } from "./page";
import { QueryRepository } from "./query";
import { ScraperRepository } from "./scraper";

interface IExtensions {
    scrape: ScraperRepository,
    page: PageDataRepository,
    actions: ActionRepository,
    queries: QueryRepository,
}

export {
    ScraperRepository, PageDataRepository, QueryRepository, ActionRepository
}; export type { IExtensions };

