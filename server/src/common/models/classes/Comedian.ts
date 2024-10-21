import { CreateComedianDTO } from "../interfaces/comedian.interface.js";
import { capitalized, removeBadWhiteSpace } from "../../util/primatives/stringUtil.js";

export class Comedian  {
  
  name: string;

  constructor(name: string) {
    const cleanString = removeBadWhiteSpace(name)
    this.name = capitalized(cleanString);
  }

  asCreateComedianDTO = (): CreateComedianDTO => {
    return {
      name: this.name
    }
  }
}