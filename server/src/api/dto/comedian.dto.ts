import { Optional } from 'sequelize'

export type CreateComedianDTO = {
  name: string;
  slug?: string;
}

export type UpdateComedianDTO = Optional<CreateComedianDTO, 'name'>

export type FilterComediansDTO = {
  isDeleted?: boolean
  includeDeleted?: boolean
}