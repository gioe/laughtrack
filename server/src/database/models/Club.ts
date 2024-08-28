import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';
import Show from './Show.js';

interface ClubAttributes {
    id: number;
    name: string;
    baseUrl: string;
    schedulePageUrl: string
    timezone: string
    scrapingConfig: any;
    slug?: string;
    createdAt?: Date;
    updatedAt?: Date;
    deletedAt?: Date;
};

export interface ClubInput extends Optional<ClubAttributes, 'id' | 'slug'> {}

export interface ClubOuput extends Required<ClubAttributes> {}

class Club extends Model<ClubAttributes, ClubInput> implements ClubAttributes {
  public id!: number
  public name!: string
  public baseUrl!: string
  public schedulePageUrl!: string
  public timezone!: string
  public slug!: string
  public scrapingConfig!: any
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
  public readonly deletedAt!: Date;
}

Club.init({
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  slug: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  baseUrl: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: false
  },
  schedulePageUrl: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  timezone: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: false
  },
  scrapingConfig: {
    type: DataTypes.JSON,
    allowNull: false,
    unique: false
  },
}, {
  timestamps: true,
  sequelize: sequelizeConnection,
  paranoid: true
})

Club.hasMany(Show)
Club.belongsTo(Show)

export default Club;



