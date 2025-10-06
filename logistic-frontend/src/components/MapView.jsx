import React, { useState } from "react";
import { MapContainer, Marker, Polygon, TileLayer, useMapEvents } from "react-leaflet";

// Компонент выделения области на карте
function SelectArea({ onChange }) {
    // points хранит координаты кликов
    const [points, setPoints] = useState([]);

    // Для обработки кликов по карте
    useMapEvents({
        click(e) {
            if (points.length < 2) {
                // Добавление новой точки
                const newPoints = [...points, e.latlng];
                setPoints(newPoints);

                if (newPoints.length === 2) {
                    // callback с координатами прямоугольника
                    const [p1, p2] = newPoints;
                    const bounds = [
                        [Math.min(p1.lat, p2.lat), Math.min(p1.lng, p2.lng)], // нижний левый угол
                        [Math.min(p1.lat, p2.lat), Math.max(p1.lng, p2.lng)], // нижний правый угол
                        [Math.max(p1.lat, p2.lat), Math.max(p1.lng, p2.lng)], // верхний правый угол
                        [Math.max(p1.lat, p2.lat), Math.min(p1.lng, p2.lng)], // верхний левый угол
                    ];
                    onChange(bounds);
                }
            } else {
                // Сброс при третьем клике
                setPoints([e.latlng]);
                onChange(null);
            }
        }
    });

    return (
        <>
            {/* Рендер маркеров */}
            {points.map((p, idx) => <Marker key={idx} position={p} />)}

            {/* Рисуем прямоугольник */}
            {points.length === 2 && (
                <Polygon
                    positions={[
                        [Math.min(points[0].lat, points[1].lat), Math.min(points[0].lng, points[1].lng)],
                        [Math.min(points[0].lat, points[1].lat), Math.max(points[0].lng, points[1].lng)],
                        [Math.max(points[0].lat, points[1].lat), Math.max(points[0].lng, points[1].lng)],
                        [Math.max(points[0].lat, points[1].lat), Math.min(points[0].lng, points[1].lng)],
                    ]}
                />
            )}
        </>
    );
}

// По умолчанию стоят координаты ПМПУ
export default function MapView({ center = [59.882036, 29.829662], zoom = 17, onAreaSelect }) {
    return (
        <div style={{ width: "100%", height: "500px" }}>
            <MapContainer center={center} zoom={zoom} style={{ width: "100%", height: "100%" }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; OpenStreetMap contributors' />
                {/* Компонент выделения области */}
                <SelectArea onChange={onAreaSelect} />
            </MapContainer>
        </div>
    );
}