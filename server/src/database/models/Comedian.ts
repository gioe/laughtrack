import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';

interface ComedianAttributes {
    name: string;
    slug?: string;
    id?: number;
    createdAt?: Date;
    updatedAt?: Date;
    deletedAt?: Date;
};

export interface ComedianInput extends Optional<ComedianAttributes, 'id' | 'slug'> {}

export interface ComedianOuput extends Required<ComedianAttributes> {}

class Comedian extends Model<ComedianAttributes, ComedianInput> implements ComedianAttributes {
  public id!: number
  public name!: string
  public slug!: string
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
  public readonly deletedAt!: Date;
}

Comedian.init({
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  slug: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
}, {
  timestamps: true,
  sequelize: sequelizeConnection,
  paranoid: true
})

export default Comedian;



