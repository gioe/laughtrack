import { ElementHandle } from "playwright-core";
import { CreateShowDTO } from "../data/show.interface.js";
import { CreateComedianDTO } from "../data/comedian.interface.js";

export interface Scrapable {
    $$eval(selector: string, pageFunction: any): Promise<any>;
    $eval(selector: string, pageFunction: any): Promise<any>;
    $$(selector: string): Promise<ElementHandle<SVGElement | HTMLElement>[]>
    $(selector: string, options?: { strict: boolean }): Promise<ElementHandle<SVGElement | HTMLElement> | null>;
}

export interface ScrapingOutput {
    show: CreateShowDTO;
    comedians: CreateComedianDTO[];
}