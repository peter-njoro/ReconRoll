import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function RosterSelectPage() {
    const { sessionId } = useParams();
    const navigate = useNavigate();
    const [people, setPeople] = useState([]);
    const [selectedPeople, setSelectedPeople] = useState({});
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');

    console.log('[RosterSelectPage] Component mounted, sessionId:', sessionId);

    useEffect(() => {
        const fetchPeople = async () => {
            try {
                console.log('[RosterSelectPage] Fetching people with encodings...');
                const response = await recognitionService.getPeopleWithEncodings();
                console.log('[RosterSelectPage] API Response:', response);
                
                const peopleList = Array.isArray(response.data.people) 
                    ? response.data.people 
                    : [];
                console.log('[RosterSelectPage] Extracted people list:', peopleList);
                
                setPeople(peopleList);
                setError(null);
            } catch (err) {
                console.error('[RosterSelectPage] Error fetching people:', err);
                setError('Failed to load people. Please try again.');
                setPeople([]);
            } finally {
                setLoading(false);
            }
        };

        fetchPeople();
    }, []);

    const handleToggle = (personId) => {
        setSelectedPeople(prev => ({
            ...prev,
            [personId]: !prev[personId]
        }));
    };

    const handleSelectAll = () => {
        const filteredPeople = getFilteredPeople();
        const allSelected = filteredPeople.every(person => selectedPeople[person.id]);

        if (allSelected) {
            // Deselect all
            const newSelection = {};
            filteredPeople.forEach(person => {
                newSelection[person.id] = false;
            });
            setSelectedPeople(newSelection);
        } else {
            // Select all
            const newSelection = { ...selectedPeople };
            filteredPeople.forEach(person => {
                newSelection[person.id] = true;
            });
            setSelectedPeople(newSelection);
        }
    };

    const handleSubmit = async () => {
        const selectedIds = Object.keys(selectedPeople).filter(id => selectedPeople[id]);

        if (selectedIds.length === 0) {
            setError('Please select at least one person');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            await recognitionService.createRosterForSession(sessionId, selectedIds);
            navigate(`/session/${sessionId}`);
        } catch (err) {
            console.error('Error creating roster:', err);
            setError('Failed to save roster. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    const getFilteredPeople = () => {
        if (!searchTerm.trim()) {
            return people;
        }

        const term = searchTerm.toLowerCase();
        return people.filter(person =>
            person.name.toLowerCase().includes(term) ||
            person.identification_number.toLowerCase().includes(term) ||
            (person.email && person.email.toLowerCase().includes(term))
        );
    };

    const filteredPeople = getFilteredPeople();
    const selectedCount = Object.values(selectedPeople).filter(Boolean).length;

    if (loading) {
        return (
            <div className="roster-page">
                <div className="container-lg">
                    <div className="loading-state">
                        <span className="spinner"></span>
                        <p>Loading available people...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="roster-page">
            <div className="container-lg">
                <div className="roster-header">
                    <h1>Select Session Roster</h1>
                    <p className="page-subtitle">Choose the people expected to attend this session</p>
                </div>

                {error && (
                    <div className="alert-custom alert-danger">
                        <i className="bi bi-exclamation-circle"></i>
                        <span>{error}</span>
                    </div>
                )}

                <div className="roster-toolbar">
                    <div className="search-wrapper">
                        <i className="bi bi-search"></i>
                        <input
                            type="text"
                            className="search-input"
                            placeholder="Search by name, ID, or email..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    <div className="toolbar-stats">
                        <span className="stat-badge">
                            {selectedCount} selected
                        </span>
                        <button
                            className="btn-select-all"
                            onClick={handleSelectAll}
                        >
                            {filteredPeople.every(p => selectedPeople[p.id])
                                ? 'Deselect All'
                                : 'Select All'}
                        </button>
                    </div>
                </div>

                {filteredPeople.length === 0 ? (
                    <div className="empty-state">
                        <i className="bi bi-inbox"></i>
                        <h3>
                            {people.length === 0
                                ? 'No people found'
                                : 'No people match your search'}
                        </h3>
                        <p>
                            {people.length === 0
                                ? 'No people with face encodings exist in the system yet.'
                                : 'Try adjusting your search criteria.'}
                        </p>
                    </div>
                ) : (
                    <div className="roster-list">
                        {filteredPeople.map(person => (
                            <div key={person.id} className="roster-item">
                                <label className="roster-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={selectedPeople[person.id] || false}
                                        onChange={() => handleToggle(person.id)}
                                    />
                                    <span className="checkmark"></span>
                                </label>

                                <div className="roster-info">
                                    <div className="info-main">
                                        <div className="person-name">{person.name}</div>
                                        <div className="person-id">{person.identification_number}</div>
                                    </div>
                                    <div className="info-secondary">
                                        {person.email && (
                                            <div className="person-email">{person.email}</div>
                                        )}
                                        <div className="encoding-count">
                                            <i className="bi bi-images"></i>
                                            {person.encoding_count} encoding{person.encoding_count !== 1 ? 's' : ''}
                                        </div>
                                    </div>
                                </div>

                                <div className="status-badge">
                                    {person.status}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <div className="roster-actions">
                    <button
                        className="btn-secondary-outline"
                        onClick={() => navigate(`/session/${sessionId}`)}
                        disabled={submitting}
                    >
                        Cancel
                    </button>
                    <button
                        className="btn-submit"
                        onClick={handleSubmit}
                        disabled={submitting || selectedCount === 0}
                    >
                        {submitting ? (
                            <>
                                <span className="spinner"></span>
                                Saving Roster...
                            </>
                        ) : (
                            <>
                                <i className="bi bi-check-circle"></i>
                                Save Roster ({selectedCount})
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
