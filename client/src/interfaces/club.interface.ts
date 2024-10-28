import { Favoritable } from "./favoritable.interface.js";
import { ShowProvider } from "./showProvider.interface.js";
import { SocialDiscoverable } from "./socialData.interface.js";
import { TagInterface } from "./tag.interface.js";
import { Taggable } from "./taggable.interface.js";

export interface ClubInterface extends ShowProvider, SocialDiscoverable, Taggable, Favoritable {
  id: number
  name: string
  baseUrl: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
  tags: TagInterface[]
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
}