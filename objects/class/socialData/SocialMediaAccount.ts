import { SocialMediaAccountInterface } from "./socialData.interface";

export class SocialMediaAccount implements SocialMediaAccountInterface {
    account?: string;
    following: number;

    constructor(account?: string, following?: number) {
        this.account = account
        this.following = following ?? 0
    }



}
