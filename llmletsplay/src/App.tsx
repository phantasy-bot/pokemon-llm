import { Routes, Route } from 'react-router-dom'
import { LandingPage } from './components/LandingPage'
import { LassLayout } from './components/LassPage' // Renamed export in file content, but filename still LassPage.tsx? Yes.
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/lass/*" element={<LassLayout />} />
    </Routes>
  )
}

export default App
