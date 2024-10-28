import { ShowProvider } from "./showProvider.interface.js";
import { SocialDiscoverable } from "./socialData.interface.js";
import { TagInterface } from "./tag.interface.js";
import { Taggable } from "./taggable.interface.js";

export interface ComedianInterface extends ShowProvider, SocialDiscoverable, Taggable {
  id: number;
  name: string;
  userIsFollower?: boolean;
  favoriteId?: number
  tags: TagInterface[]
  isFavorite: boolean;
}

export interface ComedianFilterInterface {
  id: number;
  name: string;
}
