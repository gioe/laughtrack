import { Firestore } from "@google-cloud/firestore"
import { removeAllWhiteSpace } from "../types/stringUtil.js";
import { Storable } from "../../types/storable.interface.js";

const db = new Firestore({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
});

export const updateDocument = async (
  documentReference: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, 
  storable: Storable) => {
  await documentReference.update({ lastUpdate: new Date().toDateString() });
  await documentReference.update(storable.getData());
}

export const createNewDocument = async (
  documentReference: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, 
  storable: Storable) => {
  await documentReference.set({ lastUpdate: new Date().toDateString() });
  await documentReference.set(storable.getData());
}

export const writeToFirestore = async (
  collectionName: string, 
  storable: Storable) => {
  const formattedDocName = removeAllWhiteSpace(storable.getDocumentName().toLowerCase())
  const docRef = db.collection(collectionName).doc(formattedDocName);
  const comedianDoc = await docRef.get()

  if (comedianDoc.exists) {
    updateDocument(docRef, storable)
  } else {
    createNewDocument(docRef, storable)
  }

}

export const getValuesFromCollection = async (
  collectionName: string, 
  values: string[]) => {
  const collectionRef = db.collection(collectionName)
  const allDocuments = await collectionRef.listDocuments();
  return Promise.all(allDocuments.map(docRef => getValuesFromDocumentReference(docRef, values)));
}

export const getValueFromDocument = async (
  collectionName: string, 
  docName: string,
  values: string[]) => {
  const documentReference = db.collection(collectionName).doc(docName);
  return getValuesFromDocumentReference(documentReference, values)
}

const getValuesFromDocumentReference = async (
  docRef: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>,
  values: string[]) => {
  const doc = await docRef.get();
  return getValuesFromDocument(doc, values)
}

const getValuesFromDocument = (
  doc: FirebaseFirestore.DocumentSnapshot<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>,
  values: string[]) => {
    let responseMap = new Map<string, any>();
    responseMap.set("docName", doc.id)

    values.forEach(value => {
      responseMap.set(value, doc.get(value))
    })

    return responseMap;
  };

