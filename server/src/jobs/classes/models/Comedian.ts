import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { removeBadWhiteSpace } from "../../util/stringUtil.js";

export class Comedian implements ComedianInterface {
  
  id: number = 0;
  name: string;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }

}