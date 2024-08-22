import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';

interface ShowAttributes {
    id: number;
    slug: string;
    dateTime: Date;
    ticketLink: string;
    createdAt?: Date;
    updatedAt?: Date;
    deletedAt?: Date;
};

export interface ShowInput extends Optional<ShowAttributes, 'id' | 'slug'> {}

export interface ShowOutput extends Required<ShowAttributes> {}

class Show extends Model<ShowAttributes, ShowInput> implements ShowAttributes {
  public id!: number
  public slug!: string; 
  public ticketLink!: string
  public dateTime!: Date
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
  public readonly deletedAt!: Date;
}

Show.init({
  id: {
    type: DataTypes.INTEGER.UNSIGNED,
    autoIncrement: true,
    primaryKey: true,
  },
  slug: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  dateTime: {
    type: DataTypes.DATE,
    allowNull: false,
  },
  ticketLink: {
    type: DataTypes.STRING,
    allowNull: false
  },
}, {
  timestamps: true,
  sequelize: sequelizeConnection,
  paranoid: true
});

export default Show;
