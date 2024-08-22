import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';

interface ClubAttributes {
    id: number;
    slug: string;
    name: string;
    baseUrl: string;
    schedulePageUrl: string;
    timezone: string;
    createdAt?: Date;
    updatedAt?: Date;
    deletedAt?: Date;
};

export interface ClubInput extends Optional<ClubAttributes, 'id' | 'slug'> {}

export interface ClubOuput extends Required<ClubAttributes> {}

class Club extends Model<ClubAttributes, ClubInput> implements ClubAttributes {
  public id!: number
  public name!: string
  public slug!: string
  public baseUrl!: string
  public schedulePageUrl!: string
  public timezone!: string
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
  public readonly deletedAt!: Date;
}

Club.init({
  id: {
    type: DataTypes.INTEGER.UNSIGNED,
    autoIncrement: true,
    primaryKey: true,
  },
  slug: {
    type: DataTypes.INTEGER.UNSIGNED,
    autoIncrement: true,
    primaryKey: true,
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  baseUrl: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  schedulePageUrl: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  timezone: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
}, {
  timestamps: true,
  sequelize: sequelizeConnection,
  paranoid: true
})

export default Club;



