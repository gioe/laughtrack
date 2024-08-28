import { DataTypes, Model, Optional } from 'sequelize';
import sequelizeConnection from '../config.js';
import Show from './Show.js';

interface ClubAttributes {
    id: string;
    name: string;
    baseUrl: string;
    schedulePageUrl: string
    timezone: string
    scrapingConfig: any;
};

export interface ClubCreationAttributes extends Optional<ClubAttributes, 'id'> {}
export interface ClubOuput extends Required<ClubAttributes> {}

interface ClubInstance
  extends Model<ClubAttributes, ClubCreationAttributes>,
    ClubAttributes {
      createdAt?: Date;
      updatedAt?: Date;
      deletedAt?: Date;
    }


const Club = sequelizeConnection.define<ClubInstance>(
  'Club',
  {
  id: {
    allowNull: false,
    autoIncrement: false,
    primaryKey: true,
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    unique: true,
  },
  name: {
    type: DataTypes.TEXT,
    allowNull: false
  },
  baseUrl: {
    type: DataTypes.TEXT,
    allowNull: false,
    unique: false
  },
  schedulePageUrl: {
    type: DataTypes.TEXT,
    allowNull: false,
    unique: true
  },
  timezone: {
    type: DataTypes.TEXT,
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
  paranoid: true
})

Club.hasMany(Show, {
  sourceKey: 'id',
  foreignKey: 'clubId',
  as: 'shows'
});

Show.belongsTo(Club, {
  foreignKey: 'clubId',
  as: 'club'
});

export default Club;



