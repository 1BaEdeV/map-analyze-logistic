import React, { useState } from "react";
import MapView from "../components/MapView";

export default function AnalysisPage() {
    // Режим анализа: File - загружаем карту, Map - выбираем участок на карте
    const [mode, setMode] = useState("file");

    // Состояния для загруженного файла и превью
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);

    // Состояние выбранной области
    const [selectedArea, setSelectedArea] = useState(null);

    // Выбор файла
    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];
        if (!selectedFile) return;

        setFile(selectedFile);

        const reader = new FileReader(); // Читаем файл в памяти браузера
        reader.onload = (e) => setPreview(e.target.result); // Сохраняем результат в Preview
        reader.readAsDataURL(selectedFile); // Преобразуем файл  в строку
    };

    // Кнопка "Начать Анализ"
    const handleAnalyze = () => {
        if (mode === "file") {
            if (!file) {
                alert("Выберите файл для карты!");
                return;
            }

            // TODO: Вызов API для анализа
            console.log("Отправка файла на сервер:", file);
            alert("Файл отправлен на сервер");

        } else if (mode === "map") {
            if (!selectedArea) {
                alert("Выделите участок карты для анализа!");
                return;
            }

            // TODO: Логика обработки выделенного участка карты
            console.log("Отправка выделенного участка карты");
            alert("Участок карты отправлен на сервер");
        }

    };


    return (
        <div>
            <h1>Анализ Карты</h1>
            <p> Карта и визуализация Графа</p>
            <p> Выберите способ анализа</p>

            {/* Переключатель режима */}
            <div style={{ marginBottom: 16 }}>
                <label>
                    <input
                        type="radio"
                        name="mode"
                        value="file"
                        checked={mode === "file"}
                        onChange={() => setMode("file")}
                    />
                    Загрузить файл
                </label>
                <label style={{ marginLeft: 16 }}>
                    <input
                        type="radio"
                        name="mode"
                        value="map"
                        checked={mode === "map"}
                        onChange={() => setMode("map")}
                    />
                    Использовать карту
                </label>
            </div>

            {/* Блок загрузки файла */}
            {mode === "file" && (
                <div>
                    <div style={{ marginBottom: 16 }}>
                        <input type="file" accept="image/*" onChange={handleFileChange} />
                    </div>
                    {/* Превью карты */}
                    {file && (
                        <div>
                            <p>Выбран файл: {file.name}</p>
                            {preview && (
                                <img
                                    src={preview}
                                    alt="Превью карты"
                                    style={{ maxWidth: "100%", maxHeight: 300, border: "1px solid #ccc", }} />
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Блок выбора Leaflet карты */}
            {mode === "map" && (
                <div style={{ marginBottom: 16 }}>
                    <h2>Карта региона</h2>
                    <MapView onAreaSelect={setSelectedArea} />
                    {selectedArea && <p>Область выбрана для анализа</p>}
                </div>
            )}

            {/* Кнопка запуска анализа */}
            <button onClick={handleAnalyze}>Начать Анализ</button>
        </div>
    );
}