import { isLocal } from './environmentUtil.js';
import { readFileFromFileSystem } from './fileSystemUtil.js';
import { readFileFromBucket } from './gcp/cloudStorageUtil.js';

export async function readFile(fileName: string): Promise<string> {
    if (isLocal) {
        return readFileFromFileSystem(fileName)
    } else {
        return readFileFromBucket(fileName)
    }
}