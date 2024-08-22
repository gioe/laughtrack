export interface Club {
    id: number
    name: string
    slug: string
    baseUrl: string;
    schedulePageUrl: string;
    timezone: string;
    createdAt: Date
    updatedAt: Date
    deletedAt?: Date 
  }