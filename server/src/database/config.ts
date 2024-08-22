import {  Dialect, Model, Sequelize } from 'sequelize'
import diff from 'microdiff'
import { SequelizeHooks } from 'sequelize/lib/hooks'
import localCache from '../lib/local-cache.js'
import pg from 'pg'

const hooks: Partial<SequelizeHooks<Model<any, any>, any, any>> = {
  afterUpdate: (instance: Model<any, any>) => {
    const cacheKey = `${instance.constructor.name.toLowerCase()}s`

    const currentData = instance.get({ plain: true })

    if (!localCache.hasKey(cacheKey)) {
      return
    }

    const listingData = localCache.get<any>(cacheKey) as any[]
    const itemIndex = listingData.findIndex((it) => it.id === instance.getDataValue('id'))
    const oldItemData = ~itemIndex ? listingData[itemIndex] : {}

    const instanceDiff = diff(oldItemData, currentData)

    if (instanceDiff.length > 0) {
      listingData[itemIndex] = currentData
      localCache.set(cacheKey, listingData)
    }
  },
  afterCreate: (instance: Model<any, any>) => {
    const cacheKey = `${instance.constructor.name.toLowerCase()}s`
    const currentData = instance.get({ plain: true })

    if (!localCache.hasKey(cacheKey)) {
      return
    }

    const listingData = localCache.get<any>(cacheKey) as any[]
    listingData.push(currentData)

    localCache.set(cacheKey, listingData)
  },
}

const sequelizeConnection = new Sequelize(process.env.POSTGRES_DB as string, 
  process.env.POSTGRES_USER as string, 
  process.env.POSTGRES_PASSWORD as string, {
    host: process.env.POSTGRES_HOST as string,
    port: process.env.POSTGRES_PORT as unknown as number,
    dialect: process.env.POSTGRES_DRIVER as Dialect,
    dialectModule: pg,
    logging: false,
    define: {hooks}
  })
  
  export default sequelizeConnection