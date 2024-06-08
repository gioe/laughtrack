import { HTMLConfigurable } from "./configs.interface.js";
import { Writable } from "./writable.interface.js";

export interface Club extends Writable, HTMLConfigurable {
    name: string;
    website: string;
    scraper: string;
}