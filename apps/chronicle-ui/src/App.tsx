import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { FolderLayout } from './layout/FolderLayout';
import { Timeline } from './pages/Timeline';
import { ContentPage } from './pages/ContentPage';
import { Admin } from './pages/Admin';

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<FolderLayout />}>
          <Route path="/" element={<Timeline />} />
          <Route path="/content/:id" element={<ContentPage />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
