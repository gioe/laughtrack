import { SocialDataDTO, SocialDataInterface } from "./socialData.interface";
import { LineupSocialDataDTO } from "../comedian/comedianLineup.interface";
import { SocialMediaAccount } from "./SocialMediaAccount";

export class SocialData implements SocialDataInterface {
    instagram: SocialMediaAccount;
    tiktok: SocialMediaAccount;
    youtube: SocialMediaAccount;
    website: string;
    linktree: string;
    popularityScore: number | null;

    // Lineup payloads hydrate only {id, popularity}; absent social fields
    // normalize to null/empty exactly like explicit DB nulls do.
    constructor(input: SocialDataDTO | LineupSocialDataDTO) {
        this.instagram = new SocialMediaAccount(input.instagramAccount ?? null, input.instagramFollowers ?? null);
        this.tiktok = new SocialMediaAccount(input.tiktokAccount ?? null, input.tiktokFollowers ?? null);
        this.youtube = new SocialMediaAccount(input.youtubeAccount ?? null, input.youtubeFollowers ?? null);
        this.linktree = input.linktree ?? ""
        this.website = input.website ?? ""
        this.popularityScore = input.popularity;
    }

    hasInstagramAccount() {
        return this.instagram?.account !== undefined
    }

    hasTiktokAccount() {
        return this.tiktok?.account !== undefined
    }

    hasYoutubeAccount() {
        return this.youtube?.account !== undefined
    }

}
