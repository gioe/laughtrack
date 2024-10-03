import { removeBadWhiteSpace } from "../util/stringUtil.js";

export class Comedian  {
  
  name: string;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }

}