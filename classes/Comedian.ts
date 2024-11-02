import { CreateComedianDTO } from "../interfaces";
import {
    removeBadWhiteSpace,
    capitalized,
} from "../util/primatives/stringUtil";

export class Comedian {
    name: string;

    constructor(name: string) {
        const cleanString = removeBadWhiteSpace(name);
        this.name = capitalized(cleanString);
    }

    asCreateComedianDTO = (): CreateComedianDTO => {
        return {
            name: this.name,
        };
    };
}
