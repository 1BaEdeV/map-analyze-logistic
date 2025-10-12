import React, { useState } from "react";
import MapView from "../components/MapView";

export default function AnalysisPage() {
    // Состояние выбранной области
    const [selectedArea, setSelectedArea] = useState(null);

    function areaToGeoJSON(area) {
        return {
            type: "Feature",
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [area.minLng, area.minLat],
                    [area.maxLng, area.minLat],
                    [area.maxLng, area.maxLat],
                    [area.minLng, area.maxLat],
                    [area.minLng, area.minLat],
                ]]
            },
            properties: {
                zoom: area.zoom || null,
            }
        };
    }

    async function sendGeoJSON(geojson) {
        try {
            const response = await fetch("https://httpbin.org/post", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(geojson)
            });
            const data = await response.json();
            console.log("🔁 Ответ от сервера:", data.json);
            alert("✅ Участок отправлен! Проверь консоль для деталей.");
        } catch (err) {
            console.error("❌ Ошибка при отправке:", err);
            alert("Ошибка при отправке данных на сервер!");
        }
    }

    // Кнопка "Начать Анализ"
    const handleAnalyze = async () => {
        if (!selectedArea) {
            alert("Выделите участок карты для анализа!");
            return;
        }

        // TODO: Логика обработки выделенного участка карты
        // Создаём GeoJSON-объект из выбранной области
        const geojson = areaToGeoJSON(selectedArea);
        console.log("Отправляем GeoJSON:", geojson);
        await sendGeoJSON(geojson);
    };


    return (
        <div>
            <h1>Анализ Карты</h1>
            <p> Выберите участок на карте для анализа</p>

            {/* Блок выбора Leaflet карты */}
            <div style={{ marginBottom: 16 }}>
                <h2>Карта региона</h2>
                <MapView onAreaSelect={setSelectedArea} />
                {selectedArea && (
                    <p style={{ color: "green" }}>
                        ✅ Область выбрана
                    </p>
                )}
            </div>

            {/* Кнопка запуска анализа */}
            <button onClick={handleAnalyze}>Начать Анализ</button>
        </div>
    );
}