import { EntityType } from "../enum";
import { EntityContainer } from "./entityContainer.interface";
import { Favoritable } from "./favoritable.interface";
import { DatabaseIdentifiable } from "./identifable.interface";
import { SocialDiscoverable } from "../class/socialData/socialData.interface";

export interface Entity
    extends DatabaseIdentifiable,
        Favoritable,
        SocialDiscoverable,
        EntityContainer {
    type: EntityType;
}
