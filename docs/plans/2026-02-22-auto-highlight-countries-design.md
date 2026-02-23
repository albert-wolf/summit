# Auto-Highlight Countries on City Search - Design Document

**Date:** 2026-02-22
**Status:** Design Approved
**Priority:** Enhance search UX - auto-select countries when searching for cities

## Overview

When a user searches for a city in the Servers pane, automatically highlight/select the country (or countries) that contain that city on the left pane, in addition to showing the city on the right pane.

## Requirements

1. **City-to-Countries Mapping:** Build a dictionary mapping each city to all countries containing it
2. **Smart Selection Logic:**
   - If search matches cities → select all countries containing those cities
   - If search matches countries only → select those countries
   - If search matches both cities and countries → prioritize cities (select countries containing matching cities)
3. **Fast Startup:** Load cached mapping on app startup for instant responsiveness
4. **Background Refresh:** Fetch fresh city data in background without blocking UI
5. **Cache Persistence:** Save city-to-countries mapping to `~/.config/summit/server_cache.json`

## Architecture

### Data Structure

```python
# Build during city loading
city_to_countries = {
    "New_York": ["United_States"],
    "London": ["United_Kingdom", "Canada"],
    "Toronto": ["Canada"],
    # ... etc
}
```

### Cache File Format

```json
{
  "version": 1,
  "city_to_countries": {
    "New_York": ["United_States"],
    "London": ["United_Kingdom", "Canada"]
  },
  "last_updated": "2026-02-22T12:34:56Z"
}
```

### Loading Strategy

1. **On Startup:**
   - Load `city_to_countries` from cache file if it exists (instant)
   - If cache missing, fetch from CLI (normal path)
   - Spawn background thread to refresh from CLI (keeps data current)

2. **During Search:**
   - Find matching cities in cache/loaded data
   - Extract their countries and auto-select them
   - Update cities display (existing behavior)

3. **Background Refresh:**
   - Fetch fresh city list in background thread
   - Rebuild city-to-countries mapping
   - Compare with cached version
   - If changed, update cache file silently
   - No UI disruption

## Implementation Locations

### `servers_pane.py`
- Add `city_to_countries` instance variable
- Add `load_city_to_countries_mapping()` to build the mapping
- Modify `on_search_changed()` to implement selection logic
- Add `select_countries_by_name()` helper to select multiple countries
- Add cache loading/saving methods
- Modify `load_all_cities()` to rebuild mapping and cache after refresh

### `summit_manager.py`
- Export city-to-countries data after fetching cities (no changes needed if we build it in servers_pane)

## Data Flow

```
App Startup
  ├─ Load city_to_countries from cache file (fast!)
  ├─ Display UI instantly
  └─ [Background] Fetch fresh cities from CLI
       └─ Rebuild mapping
       └─ Compare with cache
       └─ Update cache if changed (silent)

User Searches "New York"
  ├─ Find matching cities: ["New_York"]
  ├─ Get countries: ["United_States"]
  ├─ Auto-select "United_States" on left
  └─ Show "New_York" on right

User Searches "united"
  ├─ Find matching cities: [] (no match)
  ├─ Find matching countries: ["United_States", "United_Kingdom"]
  ├─ Auto-select both countries
  └─ Show filtered cities from those countries
```

## Success Criteria

- ✅ Searching for a city auto-selects its country
- ✅ Searching for a city that exists in multiple countries selects all of them
- ✅ Searching matches cities first (priority logic)
- ✅ Cache loads instantly on startup (no perceptible delay)
- ✅ Background refresh keeps data current without UI disruption
- ✅ Cache file persists across app launches

## Edge Cases Handled

1. **City in multiple countries** → Select all countries
2. **Search matches cities and countries** → Prioritize cities
3. **Search matches countries only** → Select those countries
4. **Empty search** → Clear selection (existing behavior)
5. **Missing cache** → Fetch normally, build cache for next launch
6. **Cache outdated** → Background refresh updates silently
