export interface HTMLConfigurable {
    clubConfig?: ClubHTMLConfiguration;
    showConfig?: ShowHTMLConfiguration;
    comedianConfig?: ComedianHTMLConfiguration;
}

export interface ClubHTMLConfiguration {
    shouldScapeByDates: boolean;
    shouldScrapeByShows: boolean;
    allShowElementsSelector?: string    
    allShowLinksSelector?: string    
    dateMenuSelector?: string;
    dateOptionsSelector?: string;
}

export interface ShowHTMLConfiguration {
    showLineupSelector?: string;
    showDateTimeSelector?: string;
    showDateSelector?: string;
    showTimeSelector?: string;
    showNameSelector?: string;
    showTicketSelector?: string;
    badTimeStrings?: string[];
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

