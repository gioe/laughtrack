export interface Club {
    id: string
    name: string
    baseUrl: string;
    schedulePageUrl: string;
    timezone: string;
    scrapingConfig: any;
    createdAt?: Date
    updatedAt?: Date
    deletedAt?: Date 
  }