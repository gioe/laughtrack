export type CreateClubOutput = {
  id: number;
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
  latitude: number;
  longitude: number;
  image_name: string;
  popularity_score: number;
}