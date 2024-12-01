import { SocialDataDTO, SocialDataInterface } from "./socialData.interface";
import { SocialMediaAccount } from "./SocialMediaAccount";

export class SocialData implements SocialDataInterface {
    instagram: SocialMediaAccount;
    tiktok: SocialMediaAccount;
    youtube: SocialMediaAccount;
    website: string;
    linktree: string;
    popularityScore?: number;

    constructor(input: SocialDataDTO) {
        this.instagram = new SocialMediaAccount(input.instagram_account, input.instagram_followers);
        this.tiktok = new SocialMediaAccount(input.tiktok_account, input.tiktok_followers);
        this.youtube = new SocialMediaAccount(input.youtube_account, input.youtube_followers);
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
