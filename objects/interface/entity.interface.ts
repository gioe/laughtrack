import { EntityType } from "../enum";
import { BannerRepresentable } from "./bannerRepresentable.interface";
import { CardRepresentable } from "./cardRepresentable.interface";
import { EntityContainer } from "./entityContainer.interface";
import { Favoritable } from "./favoritable.interface";
import { DatabaseIdentifiable } from "./identifable.interface";
import { SocialDiscoverable } from "../class/socialData/socialData.interface";
import { Taggable } from "./taggable.interface";

export interface Entity extends DatabaseIdentifiable,
    Favoritable,
    SocialDiscoverable,
    Taggable,
    BannerRepresentable,
    CardRepresentable,
    EntityContainer {
    type: EntityType;
}
