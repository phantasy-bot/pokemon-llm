import { Routes, Route } from 'react-router-dom'
import { LandingPage } from './components/LandingPage'
import { LassPage } from './components/LassPage'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/lass" element={<LassPage />} />
    </Routes>
  )
}

export default App
