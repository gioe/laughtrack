import { Schedule } from "./schedule.interface.js"

export interface ComedianInterface {
  id: number
  name: string
  instagramAccount?: string
  tikTokAccount?: string  
  website?: string,
  poplarityScore: number;
}