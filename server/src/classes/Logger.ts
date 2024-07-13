export class Logger {
    baseSite: string;
    
    constructor(baseSite: string) {
        this.baseSite = baseSite;
    }

    log = (website: string, content: any) => {
        if (website === this.baseSite) {
            console.log(content);
        }
    }
}