

import { URLParam } from "../../enum";
import { formatParamValue, getDefaultQueryParamValue } from "../../../util/primatives/paramUtil";
import { URLParams } from "../../type/urlParams";
import { ReadonlyURLSearchParams } from "next/navigation";
import { SlugWrapper } from "../slug/SlugWrapper";

export class ParamsWrapper {
    // Properties
    params = new URLSearchParams();
    private static instance: ParamsWrapper;

    static getInstance() {
        if (!ParamsWrapper.instance) {
            ParamsWrapper.instance = new ParamsWrapper();
        }
        return ParamsWrapper.instance;
    }

    static async updateWithClientParams(readOnlyParams: ReadonlyURLSearchParams) {
        this.getInstance().params = new URLSearchParams(readOnlyParams)
    }

    static async updateWithServerParams(urlParams: Promise<URLParams>): Promise<void> {
        return urlParams.then((resolvedParams: URLParams) => {
            this.getInstance().params = new URLSearchParams(resolvedParams as Record<string, string>);
        })
    }

    static setParamValue(key: URLParam, value: string | number | Date) {
        this.getInstance().params.set(key, formatParamValue(value));
    }

    static removeParamValue(key: URLParam,) {
        this.getInstance().params.delete(key);
    }

    static getParamValue(key: URLParam): string | number | undefined {
        return this.getInstance().params.get(key) ?? getDefaultQueryParamValue(key)
    }

    static asCommonFilters() {
        return {
            size: this.getSize(),
            pattern: this.getPattern(),
            offset: this.getOffset(),
            sort: this.getSort(),
        }
    }

    static asShowQueryFilters() {
        return {
            ...(ParamsWrapper.getParamValue(URLParam.City) ? { city_id: ParamsWrapper.getParamValue(URLParam.City) } : {}),
            ...(ParamsWrapper.getParamValue(URLParam.StartDate) ? { start_date: ParamsWrapper.getParamValue(URLParam.StartDate) } : {}),
            ...(ParamsWrapper.getParamValue(URLParam.EndDate) ? { end_date: ParamsWrapper.getParamValue(URLParam.EndDate) } : {}),
            ...(SlugWrapper.getSlug() ? { slug: SlugWrapper.getSlug() } : {}),
            ...this.asCommonFilters(),
        }
    }

    static asClubQueryFilters() {
        return {
            ...(SlugWrapper.getSlug() ? { slug: SlugWrapper.getSlug() } : {}),
            ...this.asCommonFilters(),
        }
    }

    static asComedianQueryFilters() {
        return {
            ...(SlugWrapper.getSlug() ? { slug: SlugWrapper.getSlug() } : {}),
            ...this.asCommonFilters(),
        }
    }

    static getPattern() {
        const queryValue = ParamsWrapper.getParamValue(URLParam.Query)
        return `%${queryValue}%`
    }

    static getOffset() {
        const size = ParamsWrapper.getParamValue(URLParam.Size) as number
        const page = ParamsWrapper.getParamValue(URLParam.Page) as number
        return size * page
    }

    static getSize() {
        return ParamsWrapper.getParamValue(URLParam.Size)
    }

    static getSort() {
        return ParamsWrapper.getParamValue(URLParam.Sort)
    }

    static asParamsString() {
        return this.getInstance().params.toString()
    }


}
