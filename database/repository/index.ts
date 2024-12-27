// Database Interface Extensions:

import { ActionRepository } from "./actions";
import { PageDataRepository } from "./page";
import { QueryRepository } from "./query";

interface IExtensions {
    page: PageDataRepository,
    actions: ActionRepository,
    queries: QueryRepository,
}

export {
    PageDataRepository, QueryRepository, ActionRepository
}; export type { IExtensions };

