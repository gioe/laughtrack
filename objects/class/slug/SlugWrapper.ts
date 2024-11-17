import { SlugInterface } from "../../interface";

export class SlugWrapper {
    // Properties
    slug: SlugInterface = {}
    private static instance: SlugWrapper;

    static getInstance() {
        if (!SlugWrapper.instance) {
            SlugWrapper.instance = new SlugWrapper();
        }
        return SlugWrapper.instance;
    }

    static setSlug(slug: string) {
        this.getInstance().slug.slug = decodeURI(slug)
    }

    static getSlug(): string | number | undefined {
        return this.getInstance().slug?.slug
    }

    static async updateSlugValue(slugPromise: Promise<SlugInterface>) {
        return slugPromise.then((resolvedSlug: SlugInterface) => {
            if (resolvedSlug.slug) {
                SlugWrapper.setSlug(resolvedSlug.slug)
            }
        });
    }

}
