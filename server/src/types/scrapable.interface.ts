import { ElementHandle } from "playwright";

export interface Scrapable {
    $$eval(selector: string, pageFunction: any): Promise<any>;
    $eval(selector: string, pageFunction: any): Promise<any>;
    $$(selector: string): Promise<ElementHandle<SVGElement | HTMLElement>[]>
}