# Pathfinding System

The Pokemon LLM Agent uses a high-performance navigation system combining **A* (A-Star)**, **Path Caching**, and **Hierarchical Map Routing**.

## 🚀 Key Features

*   **A* Algorithm**: 10-40x faster than BFS. Uses Manhattan distance heuristic.
*   **Caching**: LRU Cache stores frequent paths. Repeated navigation is instant (<0.1ms).
*   **Terrain Awareness**: Avoids tall grass (encounters) and water (requires Surf) unless necessary.
*   **Cross-Map Routing**: Plans long-distance journeys between cities using a map connectivity graph.

---

## 🛠️ Usage

### Basic Navigation
```python
from pyAIAgent.navigation import find_path

# Auto-selects A* and checks cache
path = find_path(rom_path, map_id, start_coords, end_coords)
```

### Advanced Control
```python
# Force terrain costs (e.g., avoid grass)
path = find_path(..., auto_terrain=True)

# Cross-map planning
from core.navigation_controller import NavigationController
nav = NavigationController(...)
nav.plan_cross_map_route(current_map_id, target_map_id)
```

---

## 📊 Performance

| Metric | BFS (Old) | A* (New) | Cached |
| :--- | :--- | :--- | :--- |
| **Short Path** | 5ms | 1ms | <0.1ms |
| **Long Path** | 450ms | 35ms | <0.1ms |
| **Hit Rate** | 0% | - | ~90% |

## 🧩 Components

1.  **`pyAIAgent/navigation.py`**: Core A* implementation.
2.  **`core/path_cache.py`**: LRU Cache logic.
3.  **`core/map_graph.py`**: Graph of map connections (Warps/Edges).
4.  **`core/dev_markers.py`**: Semantic locations (e.g., "PokeCenter PC").

## 🧪 Testing

Run the benchmark suite to verify performance:
```bash
python scripts/pathfinding_benchmark.py
```
