import { FieldValue, Firestore } from "@google-cloud/firestore"
import { Show } from "../../types/show.interface.js";

export const writeToFirestore = async (shows: Show[], storagePath: string) => {
  
  const db = new Firestore({
    projectId: process.env.GCP_PROJECT_ID,
    keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
  });
  
  for (const show of shows) {
    for (const comedian of show.comedians) {
      const showsRef = db.collection('shows').doc(comedian.name);
      showsRef.get()
      .then((docSnapshot) => {
        if (docSnapshot.exists) {
          showsRef.update({
            shows: FieldValue.arrayUnion({
              dateTime: show.dateTime,
              showName: show.name,
            })
          });
        } else {
          showsRef.set({
            shows: FieldValue.arrayUnion({
              dateTime: show.dateTime,
              showName: show.name,
            })
          });
        }
    });
    }
  }
}