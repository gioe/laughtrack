import { SocialDiscoverable } from "./";
import { ImageRepresentable } from "./imageRepresentable.interface";

export interface BannerProviderInterface
    extends ImageRepresentable,
        SocialDiscoverable {}
