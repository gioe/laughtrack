import { SocialData } from "../class/socialData/SocialData";
import { Entity } from "./entity.interface";

export interface CarouselEntity extends Entity {
    name: string;
    imageUrl: string;
    socialData?: SocialData;
    showCount?: number;
}
