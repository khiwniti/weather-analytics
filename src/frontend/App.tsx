import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ScientistView from './pages/ScientistView';
import PublicView from './pages/PublicView';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/scientist" element={<ScientistView />} />
        <Route path="/" element={<PublicView />} />
      </Routes>
    </Router>
  );
}

export default App;