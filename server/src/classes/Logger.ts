export class Logger {
    scrapedPage: string;
    
    constructor(scrapedPage: string) {
        this.scrapedPage = scrapedPage;
    }

    log = (website: string, content: any) => {
        if (website === this.scrapedPage) {
            console.log(content);
        }
    }
}