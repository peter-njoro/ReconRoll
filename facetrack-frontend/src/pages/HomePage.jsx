import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function HomePage() {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const routeMap = {
        enroll: '/enroll',
        sessions: '/sessions',
    };

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                const response = await recognitionService.getInfo();
                setInfo(response.data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchInfo();
    }, []);

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div className="home-page">
            <h1>{info.title}</h1>
            <p>{info.message}</p>
            <h2>API Version: {info.version}</h2>
            <h3>Available Endpoints:</h3>

            <ul>
                {Object.entries(info.endpoints).map(([key]) => (
                    <li key={key}>
                        <Link to={routeMap[key]}>
                            {key}
                        </Link>
                    </li>
                ))}
            </ul>

        </div>
    );
}