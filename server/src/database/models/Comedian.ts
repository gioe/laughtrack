import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';

interface ComedianAttributes {
  id: string;
  name: string;
};

export interface ComedianCreationAttributes extends Optional<ComedianAttributes, 'id'> { }
export interface ComedianOuput extends Required<ComedianAttributes> { }

interface ComedianInstance
  extends Model<ComedianAttributes, ComedianCreationAttributes>,
  ComedianAttributes {
  createdAt?: Date;
  updatedAt?: Date;
  deletedAt?: Date;
}

const Comedian = sequelizeConnection.define<ComedianInstance>(
  "Comedian",
  {
    id: {
      allowNull: false,
      autoIncrement: false,
      primaryKey: true,
      type: DataTypes.UUID,
      unique: true,
    },
    name: {
      type: DataTypes.STRING,
      allowNull: false
    },
  }, {
  timestamps: true,
  paranoid: true
})

export default Comedian;



