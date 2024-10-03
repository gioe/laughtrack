export interface CreateClubDTO {
  id: number;
  name: string;
  city: string;
  address: string
  base_url: string;
  schedule_page_url: string
  timezone: string;
  scraping_config: any;
  zip_code: string;
  popularity_score: number;
}