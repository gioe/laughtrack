import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';

interface ShowAttributes {
    id: number;
    dateTime?: Date;
    ticketLink?: string;
    slug?: string;
    createdAt?: Date;
    updatedAt?: Date;
    deletedAt?: Date;
};

export interface ShowInput extends Optional<ShowAttributes, 'id' | 'slug'> {}

export interface ShowOutput extends Required<ShowAttributes> {}

class Show extends Model<ShowAttributes, ShowInput> implements ShowAttributes {
  public id!: number
  public dateTime!: Date
  public ticketLink!: string
  public slug!: string; 
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
  public readonly deletedAt!: Date;
}

Show.init({
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  dateTime: {
    type: DataTypes.DATE,
    allowNull: false,
  },
  ticketLink: {
    type: DataTypes.STRING,
    allowNull: false
  },
  slug: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  }
}, {
  timestamps: true,
  sequelize: sequelizeConnection,
  paranoid: true
});

export default Show;
