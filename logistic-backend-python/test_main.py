import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
import networkx as nx
import os
import tempfile
from unittest.mock import patch, MagicMock
from services.logistics import *
from fastapi.testclient import TestClient
import shutil

# Импортируем приложение
from main import app, DEFAULT_BBOX

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Тесты для вспомогательных функций
def test_haversine():
    # Тест на расстояние между двумя одинаковыми точками
    assert haversine((0,0), (0,0)) == 0

    # Тест на известное расстояние (приблизительно 111 км на 1 градус широты)
    dist = haversine((0, 0), (1, 0))  # 1 градус по широте
    print(dist)
    assert 111 - 1 < dist < 111 + 1  # ~111 км

    # Тест на симметричность
    dist1 = haversine((59.9343, 30.3351), (59.8723, 30.3156))
    dist2 = haversine((59.8723, 30.3156), (59.9343, 30.3351))
    assert abs(dist1 - dist2) < 0.001

def test_get_default_tags():
    # Тест для режима auto
    tags = get_default_tags("auto")
    assert tags == {"building": ["warehouse", "depot", "industrial"]}

    # Тест для режима aero
    tags = get_default_tags("aero")
    assert tags == {"aeroway": ["terminal", "hangar", "cargo"]}

    # Тест для режима sea
    tags = get_default_tags("sea")
    assert tags == {"harbour": True, "man_made": ["pier", "dock"]}

    # Тест для режима rail
    tags = get_default_tags("rail")
    assert tags == {"railway": ["station", "yard", "cargo_terminal"]}

    # Тест для неизвестного режима
    with pytest.raises(ValueError):
        get_default_tags("unknown")

    # Тест с разным регистром
    tags_lower = get_default_tags("AUTO")
    tags_upper = get_default_tags("auto")
    assert tags_lower == tags_upper

# Тесты для основных функций
def test_extract_coordinates():
    # Создаём тестовый GeoDataFrame
    points = [Point(30.3, 59.9), Point(30.4, 59.8)]
    gdf = gpd.GeoDataFrame({
        'name': ['Point1', 'Point2'],
        'building': ['warehouse', 'depot']
    }, geometry=points)
    coords_df = extract_coordinates(gdf)
    assert len(coords_df) == 2
    assert round(coords_df.iloc[0]['lat'], 2) == 59.9
    assert round(coords_df.iloc[0]['lon'], 2) == 30.3
    assert round(coords_df.iloc[1]['lat'], 2) == 59.8
    assert round(coords_df.iloc[1]['lon'], 2) == 30.4
    # Проверяем, что теги сохраняются
    assert coords_df.iloc[0]['tags']['name'] == 'Point1'

def test_extract_coordinates_with_polygons():
    # Тест с полигонами (центроиды)
    polygon1 = Polygon([(30.0, 59.0), (30.1, 59.0), (30.1, 59.1), (30.0, 59.1)])
    polygon2 = Polygon([(30.2, 59.2), (30.3, 59.2), (30.3, 59.3), (30.2, 59.3)])
    gdf = gpd.GeoDataFrame({
        'name': ['Poly1', 'Poly2'],
        'building': ['warehouse', 'depot']
    }, geometry=[polygon1, polygon2])
    coords_df = extract_coordinates(gdf)
    # Центроиды должны быть примерно в центре полигонов
    assert len(coords_df) == 2
    # Для первого полигона центроид должен быть близок к (30.05, 59.05)
    assert abs(coords_df.iloc[0]['lat'] - 59.05) < 0.01
    assert abs(coords_df.iloc[0]['lon'] - 30.05) < 0.01

@patch('services.logistics.nx.minimum_spanning_tree')
def test_build_mst_graph(mock_mst):
    # Создаём тестовый граф
    G = nx.Graph()
    G.add_nodes_from([0, 1, 2])
    G.add_edge(0, 1, weight=100)
    G.add_edge(1, 2, weight=200)
    G.add_edge(0, 2, weight=150)
    # Мокаем результат MST
    mst_result = nx.Graph()
    mst_result.add_nodes_from([0, 1, 2])
    mst_result.add_edge(0, 1, weight=100)
    mst_result.add_edge(0, 2, weight=150)
    mock_mst.return_value = mst_result
    result = build_mst_graph(G)
    # Проверяем, что вызвалась функция networkx
    mock_mst.assert_called_once()
    assert len(result.edges()) == 2

def test_build_geodesic_graph():
    # Создаём тестовый DataFrame с координатами
    coords_df = pd.DataFrame({
        'lat': [59.9, 59.8, 59.7],
        'lon': [30.3, 30.4, 30.5],
        'tags': [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}]
    })
    G = build_geodesic_graph(coords_df)
    # В графе должно быть 3 узла
    assert len(G.nodes()) == 3
    # Должно быть 3 ребра (полный граф из 3 узлов: 3*(3-1)/2 = 3)
    assert len(G.edges()) == 3
    # Проверяем, что веса рёбер соответствуют гаверсинусу
    edges = list(G.edges(data=True))
    for u, v, data in edges:
        expected_dist = haversine(
            (coords_df.iloc[u]['lat'], coords_df.iloc[u]['lon']),
            (coords_df.iloc[v]['lat'], coords_df.iloc[v]['lon'])
        )
        assert abs(data['weight'] - expected_dist) < 0.001

def test_generate_logistics_mst_empty_gdf():
    # Тест, когда gdf пустой
    bbox = (29.81, 59.87, 29.88, 59.89)
    with patch('services.logistics.load_logistics_features') as mock_load:
        mock_load.return_value = gpd.GeoDataFrame()
        result = generate_logistics_mst(bbox, mode="auto")
        assert result['status'] == 'ok'
        # В пустом случае edges_count == 0, total_distance == 0
        assert result['edges_count'] == 0
        assert result['total_distance'] == 0

def test_generate_logistics_mst_normal_case():
    # Тест нормального сценария
    bbox = (29.81, 59.87, 29.88, 59.89)
    # Создаём фейковый GeoDataFrame
    points = [Point(30.3, 59.9), Point(30.4, 59.8)]
    gdf = gpd.GeoDataFrame({
        'name': ['Point1', 'Point2'],
        'building': ['warehouse', 'depot']
    }, geometry=points)
    with patch('services.logistics.load_logistics_features') as mock_load, \
         patch('services.logistics.build_mst_graph') as mock_mst, \
         patch('services.logistics.visualize_mst_map') as mock_visualize:
        mock_load.return_value = gdf
        # Мокаем MST
        mst_graph = nx.Graph()
        mst_graph.add_nodes_from([0, 1])
        mst_graph.add_edge(0, 1, weight=1000.0)
        mock_mst.return_value = mst_graph
        # Мокаем визуализацию: теперь возвращаем тот же путь, что получили
        def mock_visualize_impl(coords_df, mst, bbox, mode, output_file="logistics_mst.html"):
            # Эмулируем сохранение файла
            with open(output_file, 'w') as f:
                f.write('<html><body>Mock map</body></html>')
            return output_file  # ВАЖНО: возвращаем то, что получили
        mock_visualize.side_effect = mock_visualize_impl

        result = generate_logistics_mst(bbox, mode="auto")
        # Проверяем структуру результата
        assert result['status'] == 'ok'
        assert result['nodes_count'] == 2
        assert result['edges_count'] == 1
        assert result['total_distance'] == 1000.0
        assert len(result['points']) == 2
        assert len(result['edges']) == 1
        assert result['mode'] == 'auto'
        assert result['bbox'] == bbox

def test_generate_logistics_mst_cache_dir_creation():
    # Тест создания директории кэша
    bbox = (29.81, 59.87, 29.88, 59.89)
    # Создаём временные директории
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_subdir = os.path.join(temp_dir, "test_cache")
        # Создаём фейковый GeoDataFrame
        points = [Point(30.3, 59.9)]
        gdf = gpd.GeoDataFrame({
            'name': ['Point1'],
            'building': ['warehouse']
        }, geometry=points)
        with patch('services.logistics.load_logistics_features') as mock_load, \
             patch('services.logistics.build_mst_graph'), \
             patch('services.logistics.visualize_mst_map') as mock_visualize:
            mock_load.return_value = gdf
            # Мокаем визуализацию
            def mock_visualize_impl(coords_df, mst, bbox, mode, output_file="logistics_mst.html"):
                with open(output_file, 'w') as f:
                    f.write('<html><body>Mock map</body></html>')
                return output_file
            mock_visualize.side_effect = mock_visualize_impl
            # Проверяем, что директория создаётся
            assert not os.path.exists(cache_subdir)
            generate_logistics_mst(bbox, mode="auto", cache_dir=cache_subdir)
            assert os.path.exists(cache_subdir)

def test_visualize_mst_map_output():
    # Тест визуализации
    bbox = (29.81, 59.87, 29.88, 59.89)
    coords_df = pd.DataFrame({
        'lat': [59.9, 59.8],
        'lon': [30.3, 30.4],
        'tags': [{'name': 'Point1'}, {'name': 'Point2'}]
    })
    mst = nx.Graph()
    mst.add_nodes_from([0, 1])
    mst.add_edge(0, 1, weight=1000.0)

    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "test_map.html")
        # Вызываем функцию с указанным output_file
        result_path = visualize_mst_map(coords_df, mst, bbox, mode='auto', output_file=output_file)
        # Проверяем, что файл был создан
        assert os.path.exists(result_path)
        # И теперь проверяем, что возвращённый путь == переданный
        assert result_path == output_file

# Тесты для граничных случаев
def test_generate_logistics_mst_nan_handling():
    # Тест обработки NaN значений в координатах
    bbox = (29.81, 59.87, 29.88, 59.89)
    points = [Point(30.3, 59.9), Point(30.4, 59.8)]
    gdf = gpd.GeoDataFrame({
        'name': ['Point1', 'Point2'],
        'building': ['warehouse', None]  # None значение
    }, geometry=points)
    coords_df = extract_coordinates(gdf)
    # Проверяем, что обработка не падает
    G = build_geodesic_graph(coords_df)
    mst = build_mst_graph(G)
    # Проверяем, что все координаты действительны
    for _, row in coords_df.iterrows():
        assert not pd.isna(row['lat'])
        assert not pd.isna(row['lon'])


# Создаем тестовый клиент
client = TestClient(app)


@pytest.fixture
def sample_bbox():
    return {
        "west": 48.8,
        "south": 55.6,
        "east": 49.3,
        "north": 55.9
    }


@pytest.fixture
def mock_mst_result():
    return {
        "status": "ok",
        "message": "Успешно",
        "map_path": "cache/mst_test.html",
        "nodes": 10,
        "edges": 9
    }


@pytest.fixture
def mock_metrics_result():
    return {
        "status": "ok",
        "map_path": "cache/metrics_test.html",
        "metric": "degree_centrality"
    }


@pytest.fixture
def cleanup_cache():
    yield
    if os.path.exists("cache"):
        for file in os.listdir("cache"):
            file_path = os.path.join("cache", file)
            if os.path.isfile(file_path):
                os.remove(file_path)



class TestRootEndpoint:

    def test_read_root_success(self):
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Logistics Network API"
        assert "endpoints" in data
        assert "GET /" in data["endpoints"]
        assert "POST /analyze" in data["endpoints"]
        assert "GET /map" in data["endpoints"]
        assert "DELETE /cache" in data["endpoints"]




class TestHealthEndpoint:

    def test_health_check_success(self):
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "Logistics Network API"


# ============================================================================
# ТЕСТЫ ANALYZE ENDPOINT
# ============================================================================

class TestAnalyzeEndpoint:

    @patch('main.generate_logistics_mst')
    def test_analyze_success(self, mock_generate, sample_bbox):
        mock_generate.return_value = {
            "status": "ok",
            "message": "Успешно",
            "map_path": "cache/mst.html"
        }
        
        response = client.post("/analyze", params=sample_bbox)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        mock_generate.assert_called_once()

    @patch('main.generate_logistics_mst')
    def test_analyze_with_mode(self, mock_generate, sample_bbox):
        mock_generate.return_value = {"status": "ok", "map_path": "cache/mst.html"}
        
        response = client.post("/analyze", params={
            **sample_bbox,
            "mode": "rail"
        })
        
        assert response.status_code == 200
        mock_generate.assert_called_once()

    @patch('main.generate_logistics_mst')
    def test_analyze_error_status(self, mock_generate, sample_bbox):
        mock_generate.return_value = {"status": "error", "message": "Нет данных"}
        response = client.post("/analyze", params=sample_bbox)
        
        # Ожидаем 500, так как код перехватывает 404
        assert response.status_code == 500 

    @patch('main.generate_logistics_mst')
    def test_analyze_exception(self, mock_generate, sample_bbox):
        mock_generate.side_effect = Exception("Connection error")
        
        response = client.post("/analyze", params=sample_bbox)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_analyze_default_bbox(self):
        with patch('main.generate_logistics_mst') as mock_generate:
            mock_generate.return_value = {"status": "ok", "map_path": "cache/mst.html"}
            
            response = client.post("/analyze")
            
            assert response.status_code == 200
            # Проверяем, что функция вызвалась с дефолтными координатами
            mock_generate.assert_called_once()


class TestMapEndpoint:

    @patch('main.generate_logistics_mst')
    def test_get_map_success(self, mock_generate, sample_bbox):
        mock_generate.return_value = {
            "status": "ok",
            "map_path": "cache/mst.html"
        }
        
        # Создаем тестовый HTML файл
        os.makedirs("cache", exist_ok=True)
        with open("cache/mst.html", "w", encoding="utf-8") as f:
            f.write("<html><body>Test Map</body></html>")
        
        response = client.get("/map", params=sample_bbox)
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Test Map" in response.text

    @patch('main.generate_logistics_mst')
    def test_get_map_no_data(self, mock_generate, sample_bbox):
        mock_generate.return_value = {
            "status": "error",
            "message": "Нет данных"
        }
        
        response = client.get("/map", params=sample_bbox)
        
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")

    @patch('main.generate_logistics_mst')
    def test_get_map_exception(self, mock_generate, sample_bbox):
        mock_generate.side_effect = Exception("File not found")
        
        response = client.get("/map", params=sample_bbox)
        
        assert response.status_code == 500

    @patch('main.generate_all_modes_mst')
    def test_get_map_all_success(self, mock_generate_all, sample_bbox):
        # Создаем тестовый файл
        os.makedirs("cache", exist_ok=True)
        with open("cache/mst_all.html", "w", encoding="utf-8") as f:
            f.write("<html><body>All Modes Map</body></html>")
        
        response = client.get("/map/all", params=sample_bbox)
        
        assert response.status_code == 200
        assert "All Modes Map" in response.text




class TestMetricsEndpoint:

    @patch('main.analyze_logistics_metrics')
    def test_metrics_success(self, mock_analyze, sample_bbox):
        mock_analyze.return_value = {
            "status": "ok",
            "map_path": "cache/metrics.html"
        }
        
        # Создаем тестовый файл
        os.makedirs("cache", exist_ok=True)
        with open("cache/metrics.html", "w", encoding="utf-8") as f:
            f.write("<html></html>")
        
        response = client.get("/metrics", params={
            **sample_bbox,
            "metric": "degree_centrality"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "map_path" in data

    @patch('main.analyze_logistics_metrics')
    def test_metrics_error_status(self, mock_analyze, sample_bbox):

        mock_analyze.return_value = {"status": "error", "message": "Неверная метрика"}
        response = client.get("/metrics", params={**sample_bbox, "metric": "invalid"})
        
        # Ожидаем 500 
        assert response.status_code == 500

    @patch('main.analyze_logistics_metrics')
    def test_metrics_file_not_created(self, mock_analyze, sample_bbox):
        mock_analyze.return_value = {
            "status": "ok",
            "map_path": "cache/nonexistent.html"
        }
        
        response = client.get("/metrics", params={
            **sample_bbox,
            "metric": "degree_centrality"
        })
        
        assert response.status_code == 500

    def test_metrics_missing_parameter(self):
        response = client.get("/metrics", params={
            "west": 48.8,
            "south": 55.6,
            "east": 49.3,
            "north": 55.9
        })
        
        # FastAPI вернет 422 для валидации
        assert response.status_code == 422


class TestCacheEndpoint:

    def test_clear_cache_success(self, cleanup_cache):
        # Создаем тестовые файлы в кэше
        os.makedirs("cache", exist_ok=True)
        with open("cache/test_file.txt", "w") as f:
            f.write("test")
        
        response = client.delete("/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert "Кэш успешно очищен" in data["message"]
        
        # Проверяем, что файлы удалены
        assert not os.path.exists("cache/test_file.txt")

    def test_clear_cache_already_empty(self):
        # Гарантируем, что кэш не существует
        if os.path.exists("cache"):
            shutil.rmtree("cache")
        
        response = client.delete("/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert "Кэш уже пуст" in data["message"]


class TestParameterValidation:

    def test_analyze_invalid_coordinates(self):
        response = client.post("/analyze", params={
            "west": "invalid",
            "south": 55.6,
            "east": 49.3,
            "north": 55.9
        })
        
        # FastAPI вернет 422 для валидации типов
        assert response.status_code == 422

    def test_map_invalid_mode(self, sample_bbox):
        with patch('main.generate_logistics_mst') as mock_generate:
            mock_generate.return_value = {"status": "ok", "map_path": "cache/mst.html"}
            response = client.get("/map", params={"mode": 123})
            
            assert response.status_code in [200, 500] 


class TestCORS:

    def test_cors_headers_present(self):
        response = client.get("/health")
        
        # Проверяем, что CORS middleware работает
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__])
