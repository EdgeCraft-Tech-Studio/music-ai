# PatchIO Architecture Guidelines

## 🏗️ **MVC Architecture Rules**

### **Module Responsibilities**

**Controller Layer (`controllers/`):**
- ✅ **Business Logic**: Search logic, data processing, state management
- ✅ **Event Handlers**: `on_search_triggered()`, `on_mode_changed()`, `on_search_cancelled()`
- ✅ **Data Operations**: `calculate_optimal_column_widths()`, `populate_results_tree()`
- ✅ **Complex Logic**: Any business rules, algorithms, or data processing

**View Layer (`views/`):**
- ✅ **UI Updates**: `update_mode_buttons()`, `update_search_tooltip()`
- ✅ **UI State**: `show_stop_button()`, `hide_stop_button()`
- ✅ **UI Events**: `on_cancel_search_button_clicked()`, `on_start_search_clicked()`
- ✅ **Simple UI Operations**: Button visibility, tooltips, focus management

**Model Layer (`models/`):**
- ✅ **Data Access**: `get_file_icon()`, `get_file_type_info()`
- ✅ **Data Processing**: `get_matched_keywords()`, `get_genre_keywords()`
- ✅ **Data Storage**: Settings, file metadata, search results

### **Function Naming Conventions**

**Event Handlers:**
```python
# Controller handles business events
def on_search_triggered(self):      # ✅ Controller
def on_mode_changed(self):          # ✅ Controller  
def on_search_cancelled(self):      # ✅ Controller

# View handles UI events
def on_cancel_search_button_clicked(self):  # ✅ View
def on_start_search_clicked(self):          # ✅ View
```

**Data Operations:**
```python
# Controller handles complex data operations
def calculate_optimal_column_widths(self):  # ✅ Controller
def populate_results_tree(self):            # ✅ Controller

# View handles simple UI operations
def update_mode_buttons(self):              # ✅ View
def update_search_tooltip(self):            # ✅ View
```

### **Connection Patterns**

**Single Source of Truth:**
```python
# ✅ CORRECT: MVC Loader connects to controller
main_window.classic_search_button.clicked.connect(
    lambda: search_controller.on_mode_changed("classic_search")
)

# ❌ WRONG: Don't connect to view methods for business logic
main_window.simple_mode_button.clicked.connect(
    main_window.on_mode_changed  # This should be controller
)
```

**Delegation Pattern:**
```python
# ✅ CORRECT: Controller delegates UI updates to view
def on_mode_changed(self, mode: str):
    self.current_mode = mode
    # Delegate UI updates to view
    self.main_window.current_search_mode = mode
    self.main_window.update_mode_buttons()
    self.main_window.update_search_tooltip()
```

### **Function Location Rules**

**Always in Controller:**
- `on_*` event handlers for business logic
- `calculate_*` complex calculations
- `populate_*` data population
- `perform_*` business operations
- `start_*` business processes
- `cancel_*` business cancellations

**Always in View:**
- `update_*` UI updates
- `show_*` / `hide_*` UI visibility
- `set_*` UI state setters
- `get_*` simple UI getters
- `setup_*` UI setup methods

**Always in Model:**
- `get_*` data access methods
- `set_*` data setters
- `process_*` data processing
- `save_*` data persistence

### **Before Adding New Functions - Checklist**

**✅ Check these before creating any new function:**

1. **Search existing codebase** for similar function names
2. **Verify module responsibility** - is this the right place?
3. **Check connection patterns** - how will it be called?
4. **Follow naming conventions** - use consistent patterns
5. **Document the purpose** - what layer does it belong to?

### **Code Review Guidelines**

**When reviewing code, check:**
- ❌ No duplicate function names across modules
- ❌ No business logic in view layer
- ❌ No UI logic in controller layer
- ❌ No data access in view layer
- ✅ Clear separation of concerns
- ✅ Proper delegation patterns

### **Quick Reference**

**Function Location Guide:**
```
Business Events → Controller
UI Events → View  
Data Access → Model
UI Updates → View
Complex Logic → Controller
Simple Getters → View/Model
```

**Connection Flow:**
```
Button Click → Controller → Business Logic → View (UI Updates)
```

### **Common Anti-Patterns to Avoid**

**❌ DON'T:**
- Create duplicate event handlers in multiple modules
- Put business logic in view methods
- Put UI logic in controller methods
- Connect events to wrong layer methods
- Create functions with same names in different modules

**✅ DO:**
- Use single event handler per event
- Delegate UI updates from controller to view
- Keep business logic in controller
- Keep UI logic in view
- Follow naming conventions consistently

### **Memory Patterns for Development**

**Remember these key principles:**

1. **"Controller owns business logic"** - All `on_*` handlers go in controller
2. **"View owns UI updates"** - All `update_*` methods go in view  
3. **"Model owns data"** - All `get_*` data methods go in model
4. **"Single connection point"** - Each event has one handler
5. **"Delegate, don't duplicate"** - Controller delegates to view, never duplicates

### **Current Architecture Status**

**✅ Fixed Issues:**
- `on_mode_changed` - Now only in controller
- `on_search_triggered` - Now only in controller
- `on_search_cancelled` - Now only in controller
- `on_search_cleared` - Now only in controller
- `calculate_optimal_column_widths` - Now only in controller
- `populate_results_tree` - Now only in controller

**✅ Clean Architecture:**
- Single event handler per button
- Clear separation of concerns
- Proper delegation patterns
- No conflicting connections

---

**Last Updated:** Current session
**Status:** ✅ All duplicate function issues resolved
**Next Review:** Before adding any new functions 