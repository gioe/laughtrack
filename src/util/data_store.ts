import { ClubConfig } from "../types/index.js";
import { Firestore } from "@google-cloud/firestore"

export const writeToFirestore = async (object: any, clubConfig: ClubConfig) => {
    const db = new Firestore({
        projectId: process.env.GCP_PROJECT_ID,
        keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
      });
      
      const document = db.doc('posts/intro-to-firestore');

    // Enter new data into the document.
    await document.set({
      title: 'Welcome to Firestore',
      body: 'Hello World',
    });
    console.log('Entered new data into the document');
  
    // Update an existing document.
    await document.update({
      body: 'My first Firestore app',
    });
    console.log('Updated an existing document');
  
    // Read the document.
    const doc = await document.get();
    console.log('Read the document');
  
    // Delete the document.
    await document.delete();
    console.log('Deleted the document');
    }