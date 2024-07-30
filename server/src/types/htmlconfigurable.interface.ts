export interface HTMLConfigurable {
    clubConfig?: ClubHTMLConfiguration;
    showConfig?: ShowHTMLConfiguration;
    comedianConfig?: ComedianHTMLConfiguration;
}

export interface ClubHTMLConfiguration {
    shouldExpandPage: boolean;
    shouldScapeByDates: boolean;
    shouldScrapeByShows: boolean;
    allShowElementsSelector?: string    
    showPageLinkSelector?: string    
    dateMenuSelector?: string;
    dateOptionsSelector?: string;
    expansionSelector?: string;
    showLinkContainerSelector?: string
    validShowContainerSignifier?: string
}

export interface ShowHTMLConfiguration {
    showLineupSelector?: string;
    showDateTimeSelector?: string;
    showDateSelector?: string;
    showTimeSelector?: string;
    showNameSelector?: string;
    showTicketSelector?: string;
    badTimeStrings?: string[];
    badDateStrings?: string[];
    timezone: string;
}

export interface ComedianHTMLConfiguration {
    comedianWebsiteSelector?: string;
    comedianNameSelector?: string;    
    allComedianNameSelector?: string;    
    badComedianNameCharacters?: string[];
    badComedianNameStrings?: string[];
    commaPlacements?: string[];
    showSignifiers?: string[];
}

