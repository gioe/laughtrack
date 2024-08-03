export interface HTMLConfigurable {
    clubConfig: ClubHTMLConfiguration;    
    showConfig: ShowHTMLConfiguration;
    comedianConfig: ComedianHTMLConfiguration;
}

export interface ClubHTMLConfiguration {
    shouldExpandPage?: boolean;
    shouldScapeByDates?: boolean;
    shouldScrapeByShowDetails?: boolean;
    dateMenuSelector?: string;
    dateOptionsSelector?: string;
    moreShowsSelector?: string;
    showSelector?: string;
    showContainerSelector?: string;
    validShowContainerSignifier?: string;
    showDetailPageLinkSelector?: string;
}

export interface ShowHTMLConfiguration {
    dateTimeSelector?: string;
    dateSelector?: string;
    timeSelector?: string;
    dateSeparator?: string;
    ticketLinkSelector?: string;
    badDateStrings?: string[];
    badTimeStrings?: string[];
}

export interface ComedianHTMLConfiguration {
    nameSelector?: string;
    badNameCharacters?: string[];
    badNameStrings?: string[];
    showSignifiers?: string[];
}

