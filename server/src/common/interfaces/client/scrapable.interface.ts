import { ElementHandle } from "playwright-core";

export interface Scrapable {
    $$eval(selector: string, pageFunction: any): Promise<any>;
    $eval(selector: string, pageFunction: any): Promise<any>;
    $$(selector: string): Promise<ElementHandle<SVGElement | HTMLElement>[]>
    $(selector: string, options?: { strict: boolean }): Promise<ElementHandle<SVGElement | HTMLElement> | null>;
}
