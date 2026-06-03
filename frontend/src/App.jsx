import { BrowserRouter, Routes, Route } from 'react-router-dom'
import EditorPage from './pages/EditorPage'
import ViewerPage from './pages/ViewerPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<EditorPage />} />
        <Route path="/view" element={<ViewerPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
