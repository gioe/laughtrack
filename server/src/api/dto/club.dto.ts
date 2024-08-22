import { Optional } from 'sequelize'

export type CreateClubDTO = {
  name: string;
  baseUrl: string;
  schedulePageUrl: string;
  timezone: string;
  slug?: string;
}

export type UpdateClubDTO = Optional<CreateClubDTO, 'name'>

export type FilterClubsDTO = {
  isDeleted?: boolean
  includeDeleted?: boolean
}