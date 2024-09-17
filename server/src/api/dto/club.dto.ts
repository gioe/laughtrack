export type CreateClubDTO = {
  name: string;
  base_url: string;
  schedule_page_url: string;
  timezone: string;
  scraping_config: any;
}

export type CreateClubOutput = {
  id: number;
}

export type UpdateClubDTO = {
  id: number;
  name: string;
  base_url: string;
  schedule_page_url: string;
  timezone: string;
  scraping_config: any;
}

export type ClubExistenceDTO = {
  name: string;
}

export type GetClubOutput = {
  id: number;
  name: string;
  base_url: string;
  schedule_page_url: string;
  timezone: string;
  scraping_config: any;
  city: string;
  address: string;
}