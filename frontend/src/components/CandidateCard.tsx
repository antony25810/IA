// frontend/src/components/CandidateCard.tsx
import React from 'react';
import { BFSCandidate } from '../services/searchService';

interface CandidateCardProps {
    candidate: BFSCandidate;
    rank: number;
    isSelected: boolean;
    onToggleSelect: (id: number) => void;
    score?: number;
}

const CandidateCard: React.FC<CandidateCardProps> = ({
    candidate,
    rank,
    isSelected,
    onToggleSelect,
    score
}) => {
    const { attraction, distance_from_start_meters, time_from_start_minutes } = candidate;

    // Color del score
    const getScoreColor = (s: number) => {
        if (s >= 80) return '#4caf50';
        if (s >= 60) return '#ff9800';
        return '#f44336';
    };

    return (
        <div
            className={`candidate-card ${isSelected ? 'selected' : ''}`}
            onClick={() => onToggleSelect(attraction.id)}
        >
            <div className="candidate-header">
                <div className="candidate-rank">#{rank}</div>
                {score !== undefined && (
                    <div
                        className="candidate-score"
                        style={{ background: getScoreColor(score) }}
                    >
                        {score.toFixed(1)}
                    </div>
                )}
            </div>

            <h3 className="candidate-name">{attraction.name}</h3>

            <div className="candidate-meta">
                <span className="candidate-category">{attraction.category}</span>
                {attraction.rating && (
                    <span className="candidate-rating">⭐ {attraction.rating. toFixed(1)}</span>
                )}
            </div>

            {attraction.description && (
                <p className="candidate-description">
                    {attraction.description. substring(0, 100)}... 
                </p>
            )}

            <div className="candidate-stats">
                <div className="stat">
                    <span className="stat-icon">📍</span>
                    <span className="stat-value">{(distance_from_start_meters / 1000).toFixed(1)} km</span>
                </div>
                <div className="stat">
                    <span className="stat-icon">⏱️</span>
                    <span className="stat-value">{time_from_start_minutes} min</span>
                </div>
                {attraction.price_range && (
                    <div className="stat">
                        <span className="stat-icon">💰</span>
                        <span className="stat-value">{attraction.price_range}</span>
                    </div>
                )}
            </div>

            <div className="candidate-checkbox">
                {isSelected ?  '✓ Seleccionado' : 'Click para seleccionar'}
            </div>
        </div>
    );
};

export default CandidateCard;