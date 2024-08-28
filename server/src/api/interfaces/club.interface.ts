export interface Club {
    id: number
    name: string
    slug: string
    baseUrl: string;
    schedulePageUrl: string;
    timezone: string;
    scrapingConfig: any;
    createdAt: Date
    updatedAt: Date
    deletedAt?: Date 
  }