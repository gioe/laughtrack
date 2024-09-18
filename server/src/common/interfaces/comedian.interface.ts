import { Schedule } from "./schedule.interface.js"

export interface ComedianInterface {
  id: number
  name: string
  instagram?: string
  schedule?: Schedule;
  
}