export interface HTMLConfigurable {
    clubConfig?: ClubHTMLConfiguration;
    datesConfig?: DatesHTMLConfiguration;
    showConfig?: ShowHTMLConfiguration;
    comedianConfig?: ComedianHTMLConfiguration;
}

export interface ClubHTMLConfiguration {
    allShowsSelector?: string    
}

export interface DatesHTMLConfiguration {
    dateMenuSelector?: string;
    dateOptionsSelector?: string;
}

export interface ShowHTMLConfiguration {
    showLineupSelector?: string;
    showDateTimeSelector?: string;
    showNameSelector?: string;
    showTimeSelector?: string;
    showDateSelector?: string;
    showTicketSelector?: string;
}

export interface ComedianHTMLConfiguration {
    comedianWebsiteSelector?: string;
    comedianNameSelector?: string;    
    allComedianNameSelector?: string;    
}

