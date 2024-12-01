/* eslint-disable @typescript-eslint/no-empty-object-type */
import { Comedian } from "../../../../../../objects/class/comedian/Comedian";
import { ComedianInterface } from "../../../../../../objects/class/comedian/comedian.interface";

export interface EditComedianPageDTO { }
export interface EditComedianPageData extends ComedianInterface { }
export interface EditComedianPageResponse { data: Comedian }
