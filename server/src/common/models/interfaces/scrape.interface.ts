import { CreateShowDTO } from "./show.interface.js";
import { CreateComedianDTO } from "./comedian.interface.js";

export interface ScrapingOutput {
    show: CreateShowDTO;
    comedians: CreateComedianDTO[];
}