import { Storage, TransferManager, Bucket, DownloadResponse } from '@google-cloud/storage';
const storage = new Storage()
const bucket = storage.bucket(process.env.STORAGE_BUCKET as string);
bucket.setUserProject(process.env.CLOUD_STORAGE_PROJECT_ID as string);

export async function downloadBucketContents(): Promise<void> {

    const transferManager = new TransferManager(bucket);

    transferManager.downloadManyFiles(process.env.CLOUD_STORAGE_FOLDER_NAME as string, {
        passthroughOptions: {
            destination: process.env.DIRECTORY_PATH as string
        }
    })
    .catch((error: Error) => console.log(error))

}

export const readFileFromBucket = async (sourceFile: string): Promise<string> => {
    return bucket.file(sourceFile).download()
    .then((response: DownloadResponse) => JSON.parse(response[0].toString('utf8')))
    .catch((error: Error) => console.log(error))
};
