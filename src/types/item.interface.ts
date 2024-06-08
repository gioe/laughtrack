import { Club } from "./club.interface.js";
import { Comedian } from "./comedian.interface.js";
import { Show } from "./show.interface.js";

export interface Item extends Show, Comedian, Club {
    id: number;
  }

  export interface Items {
    [key: number]: Item;
  }