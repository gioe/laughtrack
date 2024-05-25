import fs from 'fs';

export const writeObjectContentsToLocalFiles = (object: any, fileName: string) => {
// Convert the object to a JSON string
const data = JSON.stringify(object, null, 2);

// Write the JSON string to a file
fs.writeFile(fileName, data, (err) => {
    if (err) throw err;
    console.log(`Data written to ${fileName}`);
});

}