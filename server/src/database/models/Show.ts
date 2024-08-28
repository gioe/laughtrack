import sequelizeConnection from '../config.js';
import { DataTypes, Model, Optional } from 'sequelize';

interface ShowAttributes {
  id: string;
  clubId: string;
  dateTime: Date;
  ticketLink: string;
  comedianIds: string[]
};


export interface ShowCreationAttributes extends Optional<ShowAttributes, 'id'> { }
export interface ShowOutput extends Required<ShowAttributes> { }

interface ShowInstance
  extends Model<ShowAttributes, ShowCreationAttributes>,
  ShowAttributes {
  createdAt?: Date;
  updatedAt?: Date;
  deletedAt?: Date;
}

const Show = sequelizeConnection.define<ShowInstance>(
  'Show',
  {
    id: {
      allowNull: false,
      autoIncrement: false,
      primaryKey: true,
      type: DataTypes.UUID,
      unique: true,
    },
    dateTime: {
      type: DataTypes.DATE,
      allowNull: false,
    },
    ticketLink: {
      type: DataTypes.TEXT,
      allowNull: false
    },
    clubId: {
      allowNull: false,
      type: DataTypes.UUID,
    },
    comedianIds: {
      allowNull: false,
      type: DataTypes.ARRAY(DataTypes.STRING),
    },
  }, {
  timestamps: true,
  paranoid: true
});

export default Show;
