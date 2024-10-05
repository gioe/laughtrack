import { CreateComedianDTO } from "../interfaces/data/comedian.interface.js";
import { removeBadWhiteSpace } from "../util/stringUtil.js";

export class Comedian  {
  
  name: string;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }

  asCreateComedianDTO = (): CreateComedianDTO => {
    return {
      name: this.name
    }
  }
}