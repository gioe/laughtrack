export interface ComedianInterface {
  id: number
  name: string
  instagramAccount?: string
  tikTokAccount?: string  
  website?: string,
  poplarityScore: number;
  instagramFollowers: number;
  tiktokFollowers: number;
  isPseudonym: boolean;
}