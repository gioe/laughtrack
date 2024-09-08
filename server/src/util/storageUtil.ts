

import { Storage, GetFilesResponse, File, GetFileMetadataCallback } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';
import { runTasks } from './promiseUtil.js';

const storage = new Storage()

export async function downloadBucketContents(bucketString: string): Promise<void> {

    const bucket = storage.bucket(bucketString);
    bucket.setUserProject(process.env.CLOUD_STORAGE_PROJECT_ID as string);

    bucket.getFiles()
    .then((response: GetFilesResponse) => downloadFiles(response[0]))
    .catch((error) => console.log(error))

}

export async function downloadFiles(files: File[]): Promise<void> {
    
    const tasks = files.map((file: File) => file.download({
        destination: getPath(file.name)
      }))

    runTasks(tasks)
    .catch((err) => console.log(err))
}

export const readFile = async (sourceFile: string): Promise<string> => {
    const filePath = getPath(sourceFile)
    return fs.readFile(filePath, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((error: Error) => console.log(error))
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
}