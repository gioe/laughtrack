

import { Storage } from '@google-cloud/storage';
import path from 'path';

import { readFile, deleteFile } from '../util/fileSystemUtil.js';
import { JSON_KEYS } from '../constants/objects.js';

export const getClubs = async () => {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destFileName = path.join(cwd, process.env.CLUBS_FILE_NAME as string)

    await downloadFile(process.env.STORAGE_BUCKET, process.env.CLUBS_FILE, destFileName)

    const clubModels = readFile(destFileName)
        .flatMap((json: any) => {
            return json[JSON_KEYS.clubs].map((club: any) => {
                return {
                    ...club,
                    scrapingConfig: json[JSON_KEYS.scrapingConfig],
                }
            })
        })

    deleteFile(destFileName);
    return clubModels;
}

export const getUsers = async () => {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destFileName = path.join(cwd, process.env.USERS_FILE_NAME as string)

    await downloadFile(process.env.STORAGE_BUCKET, process.env.USERS_FILE, destFileName)

    const users = readFile(destFileName)
    .flatMap((json: any) => {
        return json[JSON_KEYS.admins].map((object: any) => {
            return object[JSON_KEYS.email]
        })
    })
    
    deleteFile(destFileName);
    return users;
}

const downloadFile = async (bucketName: any, fileName: any, destFileName: string) => {
    const storage = new Storage();
    const options = {
        destination: destFileName,
    };
    await storage.bucket(bucketName).file(fileName).download(options);
}