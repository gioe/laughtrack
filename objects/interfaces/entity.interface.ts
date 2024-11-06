import { EntityType } from "../../util/enum";
import { Favoritable } from "./favoritable.interface";
import { Identifiable } from "./identifable.interface";
import { SocialDiscoverable } from "./socialData.interface";
import { Taggable } from "./taggable.interface";

export interface Entity extends Identifiable, Favoritable, SocialDiscoverable, Taggable {
    type: EntityType;
}
