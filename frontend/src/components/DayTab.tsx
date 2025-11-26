// frontend/src/components/DayTab.tsx
import React from 'react';
import '../app/styles/DayTab.css';

interface DayTabProps {
    dayNumber: number;
    date: string;
    isActive: boolean;
    onClick: () => void;
    attractionsCount?: number;
}

const DayTab: React. FC<DayTabProps> = ({ 
    dayNumber, 
    date, 
    isActive, 
    onClick, 
    attractionsCount 
}) => {
    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    };

    return (
        <button
            className={`day-tab ${isActive ? 'active' : ''}`}
            onClick={onClick}
        >
            <div className="day-tab-number">Día {dayNumber}</div>
            <div className="day-tab-date">{formatDate(date)}</div>
            {attractionsCount !== undefined && (
                <div className="day-tab-count">{attractionsCount} lugares</div>
            )}
        </button>
    );
};

export default DayTab;