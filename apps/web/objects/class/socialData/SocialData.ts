import { SocialDataDTO, SocialDataInterface } from "./socialData.interface";
import { SocialMediaAccount } from "./SocialMediaAccount";

export class SocialData implements SocialDataInterface {
    instagram: SocialMediaAccount;
    tiktok: SocialMediaAccount;
    youtube: SocialMediaAccount;
    website: string;
    linktree: string;
    popularityScore: number | null;

    constructor(input: SocialDataDTO) {
        this.instagram = new SocialMediaAccount(input.instagramAccount, input.instagramFollowers);
        this.tiktok = new SocialMediaAccount(input.tiktokAccount, input.tiktokFollowers);
        this.youtube = new SocialMediaAccount(input.youtubeAccount, input.youtubeFollowers);
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
