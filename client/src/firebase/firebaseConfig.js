// Import the functions you need from the SDKs you need
import { initializeApp, getApps, getApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAuth } from "firebase/auth"
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: "sknscapp.firebaseapp.com",
  projectId: "sknscapp",
  storageBucket: "sknscapp.firebasestorage.app",
  messagingSenderId: "1014040420408",
  appId: "1:1014040420408:web:778a3d80d47c1eea8b86cd",
  measurementId: "G-8DJJ8CJVFB"
};

// Initialize Firebase
const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);


export { db, app, auth };