import { SlugInterface } from "../../interface";

export class SlugWrapper {
    // Properties
    slug?: SlugInterface
    private static instance: SlugWrapper;

    static getInstance() {
        if (!SlugWrapper.instance) {
            SlugWrapper.instance = new SlugWrapper();
        }
        return SlugWrapper.instance;
    }

    static setSlug(slug: SlugInterface) {
        this.getInstance().slug = slug
    }

    static getSlug(): string | number | undefined {
        return this.getInstance().slug?.slug
    }

    static async updateSlug(slugPromise: Promise<SlugInterface>) {
        return slugPromise.then((slug: SlugInterface) => SlugWrapper.setSlug(slug));
    }

}
