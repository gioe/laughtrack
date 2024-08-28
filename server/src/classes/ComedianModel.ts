import { Comedian } from "../api/interfaces/comedian.interface.js";
import { removeBadWhiteSpace } from "../util/stringUtil.js";

export class ComedianModel implements Comedian {
  
  name: string;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }

}