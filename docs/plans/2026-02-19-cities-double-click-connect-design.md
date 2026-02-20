# Design: Double-Click Cities to Connect

**Date**: 2026-02-19
**Feature**: Connect to VPN by double-clicking a city in the Servers tab
**Status**: Approved

## Overview

Allow users to quickly connect to a VPN server by double-clicking a city in the right pane of the Servers tab, instead of requiring two actions (select country, select city, click button).

## Requirements

1. Double-click on a city triggers connection
2. Show "Connecting..." feedback in the "Connect to Selected" button
3. Button remains **enabled** during connection (user can still click it)
4. Button text returns to "Connect to Selected" once connection completes
5. Cities are only available when a country is selected (no edge case handling needed)

## Design: Approach 2 - Shared Connection Method

### Architecture

Extract connection logic into a shared `_do_connect(country, city)` method:

```
on_city_row_activated()  ──┐
                           ├──> _do_connect(country, city)
on_connect_clicked()  ─────┘    └──> background thread + UI feedback
```

### Implementation Details

**1. New Private Method: `_do_connect(country, city)`**
- Accepts country and city as parameters
- Sets button to "Connecting..." (matches current button behavior)
- Spawns background thread calling `self.nord.connect(country, city)`
- On completion, sets button back to "Connect to Selected"
- Handles success/error states

**2. Refactored Button Handler: `on_connect_clicked()`**
- Calls `_do_connect(self.selected_country, self.selected_city)`
- Eliminates duplicate connection code

**3. New Signal Handler: `on_city_row_activated()`**
- Triggered by double-click on cities listbox (GTK4 `row-activated` signal)
- Extracts city from double-clicked row
- Calls `_do_connect(self.selected_country, city)`

### Code Changes

**File**: `src/servers_pane.py`

1. Add signal connection to cities_listbox:
   ```python
   self.cities_listbox.connect("row-activated", self.on_city_row_activated)
   ```

2. Extract connection into new `_do_connect()` method:
   - Move existing button connection logic
   - Accept country/city as parameters

3. Refactor `on_connect_clicked()`:
   - Call `_do_connect(self.selected_country, self.selected_city)`

4. Add new `on_city_row_activated()` handler:
   - Extract city label from activated row
   - Call `_do_connect(self.selected_country, city)`

### UI Behavior

**Before Double-Click**:
- Cities list visible with multiple options
- Button shows "Connect to Selected"

**During Double-Click → Connection**:
- Button shows "Connecting..." (no change visually from button click)
- Button remains **enabled**
- User can click button or select different city

**After Connection Completes**:
- Button returns to "Connect to Selected"
- Connection status updates in Status tab

### Error Handling

Same as current button implementation:
- Background thread handles connection
- Errors displayed via Status tab updates
- Button always returns to "Connect to Selected"

### Testing

1. Double-click various cities → verifies connection
2. Double-click with no country selected → not possible (cities empty)
3. Click button during double-click connection → queues new connection
4. Verify button text transitions: "Connect to Selected" → "Connecting..." → "Connect to Selected"

## Implementation Plan

See: `2026-02-19-cities-double-click-connect-plan.md`
