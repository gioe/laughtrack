import { SocialMediaAccountInterface } from "./socialData.interface";

export class SocialMediaAccount implements SocialMediaAccountInterface {
    account: string | null;
    following: number;

    constructor(account: string | null, following: number | null) {
        this.account = account
        this.following = following ?? 0
    }



}
