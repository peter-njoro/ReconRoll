import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { SessionsPage } from './pages/SessionsPage';
import { SessionDetailPage } from './pages/SessionDetailPage';
import { CreateSessionPage } from './pages/CreateSessionPage';
import { EnrollmentForm } from './components/EnrollmentForm';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/enroll" element={<EnrollmentForm />} />
                <Route path="/sessions" element={<SessionsPage />} />
                <Route path="/session/create" element={<CreateSessionPage />} />
                <Route path="/session/:sessionId" element={<SessionDetailPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;