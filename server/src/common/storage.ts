

import { Storage } from '@google-cloud/storage';
import path from 'path';

import { readFile, deleteFile } from '../util/fileSystemUtil.js';
import { JSON_KEYS } from '../constants/objects.js';

export const getClubs = async () => {

    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const storage = new Storage();

    const bucketName = process.env.CLUBS_BUCKET as string;
    const fileName = process.env.CLUBS_FILE as string;
    const destFileName = path.join(cwd, process.env.DESTINATION_FILE_NAME as string)

    const options = {
        destination: destFileName,
    };

    await storage.bucket(bucketName).file(fileName).download(options);

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
