import PageInteractionConfig from "./pageInteractable.interface.js";

export interface HTMLConfigurable {
    interactionConfig: PageInteractionConfig,
    shouldExpandPage?: boolean;
    shouldScapeByDates?: boolean;
    shouldScrapeByShowDetails?: boolean;
    showScrapeShowDetailsOnDifferentPages?: boolean;
    pagesToScrape?: number;
    dateMenuSelector?: string;
    dateOptionsSelector?: string;
    moreShowsSelector?: string;
    showSelector?: string;
    showContainerSelector?: string;
    validShowContainerSignifier?: string;
    showDetailPageLinkSelector?: string;
    dateTimeSelector?: string;
    dateSelector?: string;
    timeSelector?: string;
    dateSeparator?: string;
    ticketLinkSelector?: string;
    badDateStrings?: string[];
    badTimeStrings?: string[];
    nameSelector?: string;
    badNameCharacters?: string[];
    badNameStrings?: string[];
    showSignifiers?: string[];
}


