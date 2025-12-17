# Pathfinding System Improvement Plan

## Executive Summary

Based on research into modern pathfinding algorithms and analysis of the current BFS implementation, this plan outlines improvements to make the Pokemon LLM pathfinding system faster, more reliable, and better integrated with the LLM agent's decision-making.

## Current System Analysis

### What We Have (`pyAIAgent/navigation.py`)

**Algorithm**: Basic Breadth-First Search (BFS)
- ✅ **Strengths**:
  - Simple and reliable
  - Guaranteed shortest path
  - Works on any graph structure
  - Already integrated with ROM data

- ❌ **Weaknesses**:
  - No movement costs consideration
  - Explores all directions equally (wastes computation)
  - No path caching or reuse
  - Recalculates entire path on every call
  - No support for dynamic obstacles (NPCs)
  - No hierarchical pathfinding for cross-map navigation

### Current Usage Pattern

```python
# From navigation_controller.py
path = find_path(
    rom_path,
    current_map_id,
    [current_x, current_y],
    [target_x, target_y]
)
# Returns: "R;R;D;D;L;" or None
```

## Research Findings

### A* Algorithm (Priority: HIGH)

**Source**: Wikipedia A* page, Red Blob Games tutorial

**Key Insight**: A* = Dijkstra's Algorithm + Heuristic Guidance
- **Formula**: `f(n) = g(n) + h(n)`
  - `g(n)` = actual cost from start to node n
  - `h(n)` = estimated cost from n to goal (heuristic)
  - `f(n)` = total estimated cost of path through n

**Benefits for Pokemon**:
- 10-40x faster than BFS on large maps
- Still guarantees shortest path with admissible heuristic
- Can incorporate movement costs (grass vs water vs cave)
- Explores towards goal instead of all directions

**Heuristics to Use**:
1. **Manhattan Distance** (primary): `abs(x1-x2) + abs(y1-y2)`
   - Perfect for Pokemon's 4-directional movement
   - Always admissible (never overestimates)
2. **Diagonal Distance** (if diagonal movement added): Chebyshev distance

### Jump Point Search (Priority: MEDIUM)

**Source**: Wikipedia JPS page, research papers

**Key Insight**: Skip unnecessary nodes on uniform-cost grids
- Reduces A* node expansions by 1-2 orders of magnitude
- Only works on uniform grids (perfect for Pokemon maps!)
- "Jumps" along straight lines until hitting obstacles

**Application to Pokemon**:
- Pokemon maps are uniform grids → perfect fit!
- Can handle corner-cutting rules (important for tile-based movement)
- Pre-processing can cache jump points

**Caveat**: More complex to implement, only beneficial for large open areas

### Movement Costs & Terrain Weights (Priority: HIGH)

**Source**: Red Blob Games, A* applications

**Use Cases in Pokemon**:
1. **Tall Grass**: Higher cost (encounter battles)
2. **Water**: Very high cost (need Surf HM)
3. **Ledges**: One-way movement (can't go back up)
4. **Strength Boulders**: Need HM to push
5. **Cut Trees**: Need HM to cut
6. **NPCs**: Temporary high cost (they move)

**Implementation**: Each tile gets a cost multiplier:
```python
TERRAIN_COSTS = {
    'grass_normal': 1,
    'grass_tall': 3,      # Avoid battles
    'water': 100,         # Very expensive (need Surf)
    'ledge_down': 1,      # Can jump down
    'ledge_up': 999,      # Can't climb up!
    'npc_tile': 50,       # Try to avoid
    'boulder': 100,       # Need Strength HM
}
```

### Hierarchical Pathfinding (Priority: MEDIUM-HIGH)

**Source**: Red Blob Games map representation guide

**Problem**: Cross-map navigation requires planning route through multiple maps
- Example: Pallet Town → Viridian City → Pewter City
- Current system only pathfinds within single map

**Solution**: Two-level pathfinding
1. **High-level**: Map-to-map routing (which exits to use)
2. **Low-level**: Tile-to-tile routing (A* within map)

**Benefits**:
- LLM can plan multi-map journeys
- Avoids dead-end maps
- Can estimate total journey length

### Path Caching & Reuse (Priority: HIGH)

**Source**: Game AI programming best practices

**Observation**: LLM often recalculates same paths
- Example: If path from A→B was just computed, reuse it!
- Path only invalidates if map changes or obstacles move

**Implementation**:
```python
class PathCache:
    def __init__(self):
        self._cache = {}  # (map_id, start, goal) → path
        self._cache_timestamps = {}
        
    def get(self, map_id, start, goal):
        key = (map_id, tuple(start), tuple(goal))
        if key in self._cache:
            return self._cache[key]
        return None
    
    def store(self, map_id, start, goal, path):
        key = (map_id, tuple(start), tuple(goal))
        self._cache[key] = path
        self._cache_timestamps[key] = time.time()
    
    def invalidate_map(self, map_id):
        # Clear all paths for this map
        self._cache = {k: v for k, v in self._cache.items() 
                      if k[0] != map_id}
```

### Partial Path Following (Priority: MEDIUM)

**Source**: Game AI patterns

**Problem**: Paths can be long ("R;R;R;U;U;U;L;L;L;D;D;D;...")
- If obstacle appears, entire path is wasted
- LLM should execute partial path and recompute

**Solution**: Windowed path execution
```python
def get_next_moves(path, window=4):
    """Return next N moves from path, not entire path"""
    moves = path.split(';')[:window]
    return ';'.join(moves) + ';'
```

**Current**: Navigation controller already does this!
```python
def _get_next_moves(self, path, num_moves=4):
    # Already implemented! ✅
```

### Dynamic Obstacle Handling (Priority: MEDIUM)

**Source**: Real-time pathfinding research

**Problem**: NPCs move, creating temporary obstacles
- Static pathfinding treats NPCs as permanent obstacles
- Results in paths that avoid areas where NPCs might have moved away

**Solutions**:
1. **Temporal Discount**: Lower NPC obstacle cost over time
2. **Wait Actions**: Add "wait for NPC to move" as an option
3. **Re-path on Collision**: If path blocked, immediately recompute

## Implementation Plan

### Phase 1: A* Upgrade (Week 1) - **CRITICAL PATH**

**Priority**: ⭐⭐⭐ HIGHEST

**Effort**: Medium (2-3 days)

**Tasks**:
1. Replace BFS with A* in `pyAIAgent/navigation.py`
2. Implement Manhattan distance heuristic
3. Add movement cost support
4. Maintain backward compatibility

**Expected Gains**:
- 10-40x speedup on large maps
- Enable terrain-aware pathfinding
- Foundation for future improvements

**Implementation Checklist**:
- [ ] Create `_astar_find_path()` function
- [ ] Add heuristic function (Manhattan distance)
- [ ] Modify priority queue to use f-score
- [ ] Add movement cost parameter to `find_path()`
- [ ] Update `build_quadrant_walkability()` to include costs
- [ ] Add unit tests comparing BFS vs A* results
- [ ] Benchmark performance on real Pokemon maps

### Phase 2: Path Caching (Week 1-2) - **HIGH IMPACT**

**Priority**: ⭐⭐⭐ HIGH

**Effort**: Low (1 day)

**Tasks**:
1. Create `PathCache` class
2. Integrate with navigation controller
3. Add cache invalidation on map change
4. Add LRU eviction (max 100 paths cached)

**Expected Gains**:
- Instant path retrieval for repeated goals
- Reduced computation in navigation loops
- Better LLM cycle performance

**Implementation Checklist**:
- [ ] Create `core/path_cache.py`
- [ ] Add to `navigation_controller.py`
- [ ] Cache invalidation on map transition
- [ ] LRU cache with size limit
- [ ] Logging for cache hits/misses

### Phase 3: Movement Costs & Terrain (Week 2) - **GAMEPLAY IMPACT**

**Priority**: ⭐⭐⭐ HIGH

**Effort**: Medium (2-3 days)

**Tasks**:
1. Define terrain cost mapping
2. Extract terrain type from ROM data
3. Integrate costs into A* pathfinding
4. Add HM-aware pathfinding (water requires Surf)
5. Handle one-way ledges

**Expected Gains**:
- LLM avoids tall grass when possible
- Realistic path planning around water
- Proper ledge handling

**Implementation Checklist**:
- [ ] Create `TERRAIN_COSTS` lookup table
- [ ] Parse terrain types from collision data
- [ ] Add one-way edge support (ledges)
- [ ] HM requirement checking
- [ ] Visual debugging: show cost field on minimap

### Phase 4: Hierarchical Navigation (Week 3) - **STRATEGIC**

**Priority**: ⭐⭐ MEDIUM-HIGH

**Effort**: High (4-5 days)

**Tasks**:
1. Build map connectivity graph
2. Extract exit positions from ROM
3. Implement high-level map-to-map router
4. Integrate with existing navigation controller
5. Update LLM prompts with multi-map context

**Expected Gains**:
- Cross-map journey planning
- "Go to Pewter City from Pallet Town" works end-to-end
- Better strategic decision-making

**Implementation Checklist**:
- [ ] Create `tools/build_map_graph.py` (extract map connections)
- [ ] `core/map_graph.py` for map-level pathfinding
- [ ] Integration with `navigation_controller.py`
- [ ] Update `dev_markers.py` with map transition markers
- [ ] LLM context: "To reach Pewter City, go NORTH through Viridian City"

### Phase 5: Jump Point Search (Week 4) - **OPTIMIZATION**

**Priority**: ⭐ MEDIUM

**Effort**: High (5-7 days)

**Tasks**:
1. Implement JPS for grid maps
2. Pre-process jump points
3. Handle corner-cutting rules
4. Benchmark vs A*

**Expected Gains**:
- 5-10x speedup over A* on open areas
- Negligible benefit on cramped indoor maps
- Overall 2-3x average speedup

**Implementation Checklist**:
- [ ] Study JPS papers thoroughly
- [ ] Implement basic JPS
- [ ] Add pre-processing step
- [ ] Corner-cutting rules
- [ ] Benchmark suite
- [ ] Make it optional (fallback to A*)

### Phase 6: Dynamic Obstacles & NPCs (Week 4-5) - **POLISH**

**Priority**: ⭐ MEDIUM-LOW

**Effort**: Medium (3-4 days)

**Tasks**:
1. Track NPC positions from game state
2. Add temporal NPC obstacles to pathfinding
3. Re-path on collision detection
4. Implement wait actions

**Expected Gains**:
- Smoother navigation around NPCs
- Fewer "stuck" situations
- More natural movement

**Implementation Checklist**:
- [ ] NPC position tracking in game state
- [ ] Add NPC tiles to walkability grid
- [ ] Re-pathing on path failure
- [ ] Optional "wait" action for LLM
- [ ] Collision prediction

## Testing & Validation

### Unit Tests

```python
# test_pathfinding.py
def test_astar_vs_bfs_same_result():
    """A* should find same path as BFS on uniform cost"""
    # Test on Oak's Lab, Pallet Town, Route 1
    
def test_astar_respects_terrain_costs():
    """A* should avoid high-cost terrain when possible"""
    # Create test map with water obstacle
    
def test_ledge_one_way_movement():
    """Path should not go up ledges"""
    
def test_path_cache_hit_rate():
    """Cache should reduce repeated computations"""
```

### Benchmark Suite

```python
# scripts/benchmark_pathfinding.py
- Test all algorithms on real Pokemon maps
- Measure: time, nodes explored, path length
- Compare: BFS vs A* vs JPS
- Test cases: short paths, long paths, open maps, cramped maps
```

### Integration Testing

```
- Run agent for 100 cycles
- Measure pathfinding calls, cache hits, failures
- Monitor: average time per path, stuck rate, goal completion
```

## Performance Targets

| Metric | Current (BFS) | Target (A*) | Stretch (JPS) |
|--------|---------------|-------------|---------------|
| Short path (5-10 tiles) | 5-10ms | 1-2ms | 1ms |
| Medium path (20-30 tiles) | 50-100ms | 5-15ms | 2-5ms |
| Long path (50+ tiles) | 200-500ms | 20-50ms | 10-20ms |
| Cache hit rate | 0% | 60-80% | 60-80% |
| Cross-map routing | N/A | 100-200ms | 100-200ms |

## Risk Mitigation

### Risk 1: A* Implementation Bugs

**Mitigation**:
- Keep BFS as fallback
- Extensive unit testing
- Compare A* and BFS results on same inputs

### Risk 2: Heuristic Not Admissible

**Mitigation**:
- Use proven Manhattan distance
- Validate with test cases
- Add assertion checks in debug mode

### Risk 3: Cache Invalidation Issues

**Mitigation**:
- Conservative invalidation (invalidate on any map change)
- Short TTL (5 minutes)
- Size-limited LRU cache

### Risk 4: ROM Data Parsing Errors

**Mitigation**:
- Validate collision data before use
- Add error handling for malformed data
- Fallback to BFS if parsing fails

## Success Criteria

### Must-Have (Phase 1-2)
- ✅ A* pathfinding faster than BFS
- ✅ Path cache reduces repeated computation
- ✅ All existing paths still work
- ✅ Backward compatible with current code

### Should-Have (Phase 3-4)
- ✅ Terrain costs working (grass, water, ledges)
- ✅ Cross-map navigation functional
- ✅ LLM successfully uses multi-map routing

### Nice-to-Have (Phase 5-6)
- ✅ JPS optimization in open areas
- ✅ NPC avoidance working
- ✅ Re-pathing on collision

## Resources & References

### Academic Papers
- Hart, Nilsson, Raphael (1968) - "A Formal Basis for the Heuristic Determination of Minimum Cost Paths"
- Harabor & Grastien (2011) - "Online Graph Pruning for Pathfinding on Grid Maps" (JPS)

### Online Tutorials
- Red Blob Games: Introduction to A* - https://www.redblobgames.com/pathfinding/a-star/introduction.html
- Red Blob Games: Implementation Guide - https://www.redblobgames.com/pathfinding/a-star/implementation.html

### Code Examples
- Python A* implementation: https://github.com/topics/a-star-pathfinding
- JPS+ implementation: https://github.com/facebookresearch/jps3d

## Appendix: Code Snippets

### A* Core Algorithm

```python
def _astar_find_path(grid, start, end, costs=None):
    """A* pathfinding with optional terrain costs"""
    if costs is None:
        costs = {}  # Default: all tiles cost 1
    
    def heuristic(a, b):
        # Manhattan distance
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    frontier = []  # Priority queue
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    
    while frontier:
        _, current = heapq.heappop(frontier)
        
        if current == end:
            break
        
        for next in neighbors(grid, current):
            terrain_cost = costs.get(next, 1)
            new_cost = cost_so_far[current] + terrain_cost
            
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost + heuristic(end, next)
                heapq.heappush(frontier, (priority, next))
                came_from[next] = current
    
    return reconstruct_path(came_from, start, end)
```

### Path Cache

```python
from functools import lru_cache
from collections import OrderedDict
import time

class PathCache:
    """LRU cache for pathfinding results"""
    
    def __init__(self, max_size=100, ttl=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.hits = 0
        self.misses = 0
    
    def get(self, map_id, start, goal):
        key = (map_id, tuple(start), tuple(goal))
        if key in self.cache:
            path, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return path
        
        self.misses += 1
        return None
    
    def set(self, map_id, start, goal, path):
        key = (map_id, tuple(start), tuple(goal))
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (path, time.time())
        
        # Evict oldest if over size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
```

## Timeline Summary

**Total Estimated Time**: 4-5 weeks

- **Week 1**: A* implementation + Path caching (CRITICAL)
- **Week 2**: Movement costs & terrain handling
- **Week 3**: Hierarchical navigation
- **Week 4-5**: JPS optimization + NPC handling (OPTIONAL)

**Minimum Viable Improvement**: Week 1 only (A* + caching)
- Provides 80% of the benefit with 20% of the effort
- Sets foundation for future enhancements
- Low risk, high reward
