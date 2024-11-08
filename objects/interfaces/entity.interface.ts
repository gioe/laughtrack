import { EntityType } from "../../util/enum";
import { BannerRepresentable } from "./bannerRepresentable.interface";
import { CardRepresentable } from "./cardRepresentable.interface";
import { Favoritable } from "./favoritable.interface";
import { Identifiable } from "./identifable.interface";
import { SocialDiscoverable } from "./socialData.interface";
import { Taggable } from "./taggable.interface";

export interface Entity extends Identifiable, Favoritable, SocialDiscoverable, Taggable, BannerRepresentable, CardRepresentable {
    type: EntityType;
}
