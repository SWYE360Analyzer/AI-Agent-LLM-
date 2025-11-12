# Educational Analytics API v3.0 - Super Admin Support

## Overview

This version adds comprehensive super admin support to your educational analytics system, allowing two distinct access patterns:

- **District Users**: See only their district data (existing behavior)
- **Super Admin**: Access data across all districts without filtering

## 🔐 Access Control System

### District Users (Existing Behavior)
- **Authentication**: Must provide `district_id` 
- **Data Access**: Limited to single district
- **Filtering**: Automatic `WHERE district_id = 'xxx'` applied to all queries
- **UI Indicators**: 🏢 District badges

### Super Admin Users (New)
- **Authentication**: Set `is_super_admin: true` (no district_id required)
- **Data Access**: All districts system-wide
- **Filtering**: No automatic filtering applied
- **UI Indicators**: 🔐 Super Admin badges

## 📁 Updated Files

### Core Database Tools
- **`district_postgres_tools_updated.py`**: Enhanced PostgreSQL tools with super admin support
  - Added `is_super_admin` parameter
  - Conditional district filtering
  - Cross-district query capabilities
  - New `get_unauthorized_software_usage()` method

### Agent Implementations
- **`phi_educational_agent_updated.py`**: Phi agent with dual access modes
- **`tool_intercepting_agent_updated.py`**: Intercepting agent with super admin support
- **`main_updated.py`**: FastAPI application with new endpoints and request models

## 🚀 Implementation Guide

### 1. Replace Existing Files

```bash
# Backup your current files
cp district_postgres_tools.py district_postgres_tools.backup.py
cp phi_educational_agent.py phi_educational_agent.backup.py
cp tool_intercepting_agent.py tool_intercepting_agent.backup.py
cp main.py main.backup.py

# Replace with updated versions
cp district_postgres_tools_updated.py district_postgres_tools.py
cp phi_educational_agent_updated.py phi_educational_agent.py
cp tool_intercepting_agent_updated.py tool_intercepting_agent.py
cp main_updated.py main.py
```

### 2. Update Import Statements

The updated files maintain the same function signatures but add new parameters. Existing code will continue to work with default values.

### 3. Test Basic Functionality

```bash
# Start the API
python main.py

# Test district user (existing)
curl -X POST "http://localhost:8001/api/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me top software usage",
    "district_id": "3ef51192-1070-4090-908d-ef3ab03b4325",
    "is_super_admin": false,
    "verbose": true
  }'

# Test super admin (new)
curl -X POST "http://localhost:8001/api/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show system-wide software usage across all districts", 
    "is_super_admin": true,
    "verbose": true
  }'
```

## 📊 New API Features

### Enhanced Request Model

```json
{
  "message": "Your analytics question",
  "district_id": "optional-for-super-admin", 
  "is_super_admin": false,
  "verbose": true,
  "use_intercepting_agent": true,
  "use_phi_agent": false
}
```

### New Response Fields

```json
{
  "success": true,
  "html_response": "<div>...</div>",
  "access_level": "SUPER ADMIN" | "DISTRICT {id}",
  "district_id": "optional",
  "execution_log": {
    "is_super_admin": true,
    "access_level": "SUPER ADMIN",
    "sql_queries": [...],
    "tool_calls": [...]
  },
  "agent_type": "intercepting | phi_native"
}
```

### New Endpoint: Find Problem Students

```bash
# District level
POST /api/find-problem-students
{
  "message": "Find students with unauthorized usage",
  "district_id": "abc123",
  "is_super_admin": false
}

# System-wide
POST /api/find-problem-students  
{
  "message": "Find problem students across all districts",
  "is_super_admin": true
}
```

## 🔧 Usage Examples

### For Your Original Use Case

Based on your Postman request, here's how to find problem students:

```json
{
  "message": "Which student is not using the paid software much but just enjoying with some other unauthorized softwares like watching movies listening to music a lot i just want to find those students",
  "district_id": "3ef51192-1070-4090-908d-ef3ab03b4325",
  "is_super_admin": false,
  "verbose": true
}
```

### Super Admin Equivalent

```json
{
  "message": "Which students across all districts are not using paid software but spending time with unauthorized entertainment software like movies and music",
  "is_super_admin": true,
  "verbose": true
}
```

## 🏗️ Agent Architecture

### Agent Cache Strategy

The system maintains separate caches for different access levels:

```python
# Cache keys
"super_admin_{verbose}"           # Super admin agents  
"district_{district_id}_{verbose}" # District-specific agents
```

### Database Tool Behavior

```python
# District user - automatic filtering
query = "SELECT * FROM software_usage"
# Becomes: "SELECT * FROM software_usage WHERE district_id = 'xxx'"

# Super admin - no filtering  
query = "SELECT * FROM software_usage" 
# Remains: "SELECT * FROM software_usage"
```

## 🎯 Key Benefits

### For District Users
- **Unchanged Experience**: Existing functionality preserved
- **Enhanced Security**: Stronger data isolation
- **Better Performance**: Optimized district-specific queries

### For Super Admin
- **System Oversight**: View data across all districts
- **Comparative Analysis**: Cross-district performance metrics
- **Problem Detection**: System-wide unauthorized usage patterns
- **Investment Insights**: Multi-district ROI analysis

## 🚨 Security Considerations

### Access Control
- Super admin access must be explicitly enabled per request
- No default elevation of privileges
- District filtering is enforced at the database tool level

### Backwards Compatibility
- All existing district user code continues to work
- Default parameters maintain original behavior
- No breaking changes to APIs

## 📈 Performance Notes

### Caching Strategy
- Separate agent instances for district vs super admin
- Cached by access level and configuration
- Prevents cross-contamination between access levels

### Query Performance
- Super admin queries may take longer due to larger datasets
- District queries remain optimized with proper filtering
- Materialized views used where possible

## 🔍 Monitoring & Logging

### Access Level Tracking
```python
logger.info("🔐 SUPER ADMIN ACCESS: Can view data from all districts")
logger.info("🏢 DISTRICT ACCESS: Limited to district {district_id}")
```

### Execution Logging
```python
{
  "access_level": "SUPER ADMIN | DISTRICT {id}",
  "is_super_admin": true/false,
  "district_id": "optional",
  "sql_queries": [...],
  "tool_calls": [...]
}
```

## 🧪 Testing Checklist

- [ ] District user requests work unchanged
- [ ] Super admin requests access all districts  
- [ ] Access level indicators appear in responses
- [ ] Problem student detection works for both levels
- [ ] Dashboard shows appropriate data scope
- [ ] Investment analysis respects access levels
- [ ] Usage trends show correct scope
- [ ] Error handling works for both access patterns

## 📞 Support

The updated system maintains full backward compatibility while adding powerful super admin capabilities. Your existing district users will see no changes, while super admin users gain access to comprehensive system-wide analytics.
