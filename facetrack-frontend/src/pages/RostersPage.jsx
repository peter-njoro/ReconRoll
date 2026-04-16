import { useState, useEffect } from 'react';
import { recognitionService } from '../api/recognitionService';
import './RostersPage.css';

export function RostersPage() {
    const [rosters, setRosters] = useState([]);
    const [people, setPeople] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [editingRoster, setEditingRoster] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedPeople, setSelectedPeople] = useState({});

    const [formData, setFormData] = useState({
        name: '',
        description: '',
    });

    // Load rosters and people on mount
    useEffect(() => {
        fetchRosters();
        fetchPeople();
    }, []);

    const fetchRosters = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await recognitionService.listRosters();
            setRosters(response.data.rosters || []);
        } catch (err) {
            console.error('Error fetching rosters:', err);
            setError('Failed to load rosters');
        } finally {
            setLoading(false);
        }
    };

    const fetchPeople = async () => {
        try {
            const response = await recognitionService.getPeopleWithEncodings();
            setPeople(response.data.people || []);
        } catch (err) {
            console.error('Error fetching people:', err);
            setError('Failed to load people');
        }
    };

    const openCreateModal = () => {
        setEditingRoster(null);
        setFormData({ name: '', description: '' });
        setSelectedPeople({});
        setShowModal(true);
    };

    const openEditModal = async (roster) => {
        try {
            const response = await recognitionService.getRosterDetail(roster.id);
            setEditingRoster(roster);
            setFormData({
                name: roster.name,
                description: roster.description || '',
            });

            // Pre-select people in this roster
            const newSelection = {};
            response.data.people.forEach(person => {
                newSelection[person.id] = true;
            });
            setSelectedPeople(newSelection);
            setShowModal(true);
        } catch (err) {
            console.error('Error loading roster details:', err);
            setError('Failed to load roster details');
        }
    };

    const closeModal = () => {
        setShowModal(false);
        setEditingRoster(null);
        setFormData({ name: '', description: '' });
        setSelectedPeople({});
    };

    const handleFormChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleTogglePerson = (personId) => {
        setSelectedPeople(prev => ({
            ...prev,
            [personId]: !prev[personId],
        }));
    };

    const handleSelectAll = () => {
        const filteredPeople = getFilteredPeople();
        const allSelected = filteredPeople.every(p => selectedPeople[p.id]);

        const newSelection = {};
        filteredPeople.forEach(p => {
            newSelection[p.id] = !allSelected;
        });
        setSelectedPeople(newSelection);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);

        try {
            const selectedIds = Object.keys(selectedPeople).filter(id => selectedPeople[id]);

            const rosterData = {
                name: formData.name.trim(),
                description: formData.description.trim(),
                person_ids: selectedIds,
            };

            if (!rosterData.name) {
                setError('Roster name is required');
                setSubmitting(false);
                return;
            }

            if (editingRoster) {
                await recognitionService.updateRoster(editingRoster.id, rosterData);
            } else {
                await recognitionService.createRoster(rosterData);
            }

            // Refresh rosters list
            await fetchRosters();
            closeModal();
        } catch (err) {
            console.error('Error saving roster:', err);
            const errorMsg =
                err.response?.data?.message ||
                err.response?.data?.error ||
                'Failed to save roster';
            setError(errorMsg);
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (roster) => {
        if (!window.confirm(`Are you sure you want to delete the roster "${roster.name}"?`)) {
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            await recognitionService.deleteRoster(roster.id);
            await fetchRosters();
        } catch (err) {
            console.error('Error deleting roster:', err);
            setError('Failed to delete roster');
        } finally {
            setSubmitting(false);
        }
    };

    const getFilteredPeople = () => {
        if (!searchTerm.trim()) {
            return people;
        }

        const term = searchTerm.toLowerCase();
        return people.filter(p =>
            p.name.toLowerCase().includes(term) ||
            p.identification_number.toLowerCase().includes(term)
        );
    };

    const selectedCount = Object.values(selectedPeople).filter(Boolean).length;

    if (loading) {
        return (
            <div className="rosters-page">
                <div className="container-lg">
                    <div className="loading-spinner">
                        <i className="bi bi-hourglass-split"></i>
                        <p>Loading rosters...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="rosters-page">
            <div className="container-lg">
                {/* Header */}
                <div className="rosters-header">
                    <div className="header-content">
                        <h1 className="page-title">
                            <i className="bi bi-people"></i>
                            Manage Rosters
                        </h1>
                        <p className="page-subtitle">Create and manage groups of people for attendance sessions</p>
                    </div>
                    <button
                        className="btn btn-primary"
                        onClick={openCreateModal}
                        disabled={submitting}
                    >
                        <i className="bi bi-plus-circle"></i>
                        New Roster
                    </button>
                </div>

                {/* Error Alert */}
                {error && (
                    <div className="alert alert-danger" role="alert">
                        <i className="bi bi-exclamation-circle"></i>
                        <span>{error}</span>
                        <button
                            type="button"
                            className="btn-close"
                            onClick={() => setError(null)}
                        ></button>
                    </div>
                )}

                {/* Rosters Grid */}
                {rosters.length === 0 ? (
                    <div className="empty-state">
                        <i className="bi bi-inbox"></i>
                        <h2>No Rosters Yet</h2>
                        <p>Create your first roster to get started</p>
                        <button className="btn btn-primary" onClick={openCreateModal}>
                            Create Roster
                        </button>
                    </div>
                ) : (
                    <div className="rosters-grid">
                        {rosters.map(roster => (
                            <div key={roster.id} className="roster-card">
                                <div className="roster-card-header">
                                    <h3 className="roster-name">{roster.name}</h3>
                                    <div className="roster-actions">
                                        <button
                                            className="btn btn-sm btn-outline-primary"
                                            onClick={() => openEditModal(roster)}
                                            title="Edit Roster"
                                        >
                                            <i className="bi bi-pencil"></i>
                                        </button>
                                        <button
                                            className="btn btn-sm btn-outline-danger"
                                            onClick={() => handleDelete(roster)}
                                            title="Delete Roster"
                                        >
                                            <i className="bi bi-trash"></i>
                                        </button>
                                    </div>
                                </div>

                                {roster.description && (
                                    <p className="roster-description">{roster.description}</p>
                                )}

                                <div className="roster-stats">
                                    <span className="stat">
                                        <i className="bi bi-people-fill"></i>
                                        {roster.people_count} {roster.people_count === 1 ? 'person' : 'people'}
                                    </span>
                                    <span className="stat">
                                        <i className="bi bi-calendar"></i>
                                        {new Date(roster.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>
                                {editingRoster ? 'Edit Roster' : 'Create New Roster'}
                            </h2>
                            <button
                                className="btn-close"
                                onClick={closeModal}
                                disabled={submitting}
                            ></button>
                        </div>

                        <form onSubmit={handleSubmit} className="modal-form">
                            {/* Roster Info Section */}
                            <div className="form-section">
                                <h3 className="section-title">Roster Information</h3>

                                <div className="form-group">
                                    <label htmlFor="name">Roster Name *</label>
                                    <input
                                        type="text"
                                        id="name"
                                        name="name"
                                        placeholder="e.g., Class A, Team 1"
                                        value={formData.name}
                                        onChange={handleFormChange}
                                        required
                                        disabled={submitting}
                                    />
                                </div>

                                <div className="form-group">
                                    <label htmlFor="description">Description</label>
                                    <textarea
                                        id="description"
                                        name="description"
                                        placeholder="Add details about this roster (optional)"
                                        value={formData.description}
                                        onChange={handleFormChange}
                                        rows="3"
                                        disabled={submitting}
                                    />
                                </div>
                            </div>

                            {/* People Selection Section */}
                            <div className="form-section">
                                <div className="section-header">
                                    <h3 className="section-title">Select People</h3>
                                    <span className="selection-badge">{selectedCount} selected</span>
                                </div>

                                <div className="search-box">
                                    <i className="bi bi-search"></i>
                                    <input
                                        type="text"
                                        placeholder="Search by name or ID..."
                                        value={searchTerm}
                                        onChange={e => setSearchTerm(e.target.value)}
                                        disabled={submitting}
                                    />
                                </div>

                                <div className="select-all-group">
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-secondary"
                                        onClick={handleSelectAll}
                                        disabled={submitting}
                                    >
                                        <i className="bi bi-check-all"></i>
                                        {getFilteredPeople().every(p => selectedPeople[p.id])
                                            ? 'Deselect All'
                                            : 'Select All'}
                                    </button>
                                </div>

                                <div className="people-list">
                                    {getFilteredPeople().length === 0 ? (
                                        <div className="no-results">
                                            <p>No people found</p>
                                        </div>
                                    ) : (
                                        getFilteredPeople().map(person => (
                                            <label key={person.id} className="person-item">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedPeople[person.id] || false}
                                                    onChange={() => handleTogglePerson(person.id)}
                                                    disabled={submitting}
                                                />
                                                <div className="person-info">
                                                    <span className="person-name">{person.name}</span>
                                                    <span className="person-id">{person.identification_number}</span>
                                                </div>
                                            </label>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Form Actions */}
                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={closeModal}
                                    disabled={submitting}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={submitting}
                                >
                                    {submitting ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm mr-2"></span>
                                            {editingRoster ? 'Updating...' : 'Creating...'}
                                        </>
                                    ) : (
                                        <>
                                            <i className={`bi bi-${editingRoster ? 'pencil' : 'plus-circle'}`}></i>
                                            {editingRoster ? 'Update Roster' : 'Create Roster'}
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
