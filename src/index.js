import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App'; // This looks for the 'export default' we just added

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);