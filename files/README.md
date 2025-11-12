# 🎓 Educational Software Analytics AI Agent

A district-aware AI agent built with **Phidata** that provides intelligent insights into educational software usage, ROI analysis, and compliance monitoring. The system enforces strict district-level data access controls and uses **OpenAI GPT-4o-mini** for optimal performance and cost efficiency.

## 🚀 Features

### 🔒 Security & Privacy
- **District-level data isolation** - Automatic filtering by district_id
- **Read-only database access** - No data modification capabilities
- **SQL injection protection** - Query validation and sanitization
- **Audit logging** - Complete query and response tracking

### 🧠 AI Capabilities
- **Natural language queries** - Ask questions in plain English
- **Contextual understanding** - Educational domain expertise
- **Materialized view optimization** - Leverages existing performance optimizations
- **HTML-formatted responses** - Clean, structured output for UI integration

### 📊 Analytics Features
- **Software usage trends** - Track adoption and engagement patterns
- **ROI analysis** - Cost-effectiveness and optimization recommendations
- **Security insights** - Unauthorized usage and compliance monitoring
- **Executive dashboards** - Comprehensive district-level summaries

## 🛠️ Tech Stack

- **AI Framework**: Phidata v2.7+
- **LLM**: OpenAI GPT-4o-mini (optimal cost/performance balance)
- **API**: FastAPI with async support
- **Database**: PostgreSQL with read-only access
- **Deployment**: Docker + Docker Compose
- **Security**: District-aware data filtering, SQL validation

## 📦 Quick Start

### 1. Clone and Setup

```bash
# Clone the project
git clone <your-repo>
cd educational-analytics-ai

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# PostgreSQL Configuration  
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DB=your-database-name
POSTGRES_USER=your-readonly-user
POSTGRES_PASSWORD=your-readonly-password
POSTGRES_SCHEMA=public
```

### 3. Run with Docker Compose

```bash
# Start all services (API + PostgreSQL + pgAdmin)
docker-compose up -d

# Or just the API (if you have external PostgreSQL)
docker-compose up analytics-api
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the top 5 most used software in my district",
    "district_id": "DIST001"
  }'

# Get district dashboard
curl http://localhost:8000/api/dashboard/DIST001
```

## 🌐 API Endpoints

### Core Analytics Endpoint
```
POST /api/ask
```
**Payload:**
```json
{
  "message": "What software has declining usage this quarter?",
  "district_id": "DISTRICT_123"
}
```

**Response:**
```json
{
  "success": true,
  "html_response": "<div class='analytics-result'>...</div>",
  "district_id": "DISTRICT_123",
  "sql_executed": "SELECT ... WHERE district_id = 'DISTRICT_123'"
}
```

### Pre-built Analytics Endpoints
- `GET /api/dashboard/{district_id}` - Comprehensive district dashboard
- `GET /api/roi-analysis/{district_id}` - ROI analysis and recommendations  
- `GET /api/security-insights/{district_id}` - Security and compliance insights

### Utility Endpoints
- `GET /health` - System health check
- `GET /` - API documentation homepage
- `GET /docs` - Interactive Swagger documentation
- `GET /redoc` - Alternative API documentation

## 💡 Example Queries

The AI agent understands natural language questions about educational software:

### Usage Analytics
- "Show me software with declining usage this quarter"
- "Which software has the highest engagement rates?"
- "What's the average session time for each application?"

### Financial Analysis
- "Which schools have the highest ROI software?"
- "What's our cost per student for productivity software?"
- "Find underutilized expensive software licenses"

### Security & Compliance
- "What unauthorized software is being used most?"
- "Show me unusual access patterns that might indicate security issues"
- "Which licenses are expiring in the next 30 days?"

### Comparative Analysis
- "Compare math software ROI across grade levels"
- "How does our district's usage compare to benchmarks?"
- "Which software shows seasonal usage patterns?"

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │───▶│   FastAPI App   │───▶│  PostgreSQL DB  │
│                 │    │                 │    │                 │
│ - React/Vue     │    │ - District Auth │    │ - Read-only     │
│ - HTML Display  │    │ - Query Router  │    │ - Row Level Sec │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Phidata AI    │
                       │                 │
                       │ - GPT-4o-mini   │
                       │ - District Tools│
                       │ - SQL Generator │
                       └─────────────────┘
```

## 🚦 Production Deployment

### AWS ECS Deployment

1. **Build and push to ECR:**
```bash
# Build image
docker build -t educational-analytics-ai .

# Tag for ECR
docker tag educational-analytics-ai:latest YOUR_ECR_REPO:latest

# Push to ECR
docker push YOUR_ECR_REPO:latest
```

2. **Deploy with ECS:**
```yaml
# ecs-task-definition.json
{
  "family": "educational-analytics-ai",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "analytics-api",
      "image": "YOUR_ECR_REPO:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "OPENAI_API_KEY", "value": "your-key"},
        {"name": "POSTGRES_HOST", "value": "your-rds-endpoint"}
      ]
    }
  ]
}
```

### Cloudflare Workers (Serverless)

For serverless deployment, adapt the FastAPI app to run on Cloudflare Workers:

```python
# workers-adapter.py
from fastapi import FastAPI
from educational_agent import create_educational_agent

app = FastAPI()

# Add your routes here
@app.post("/api/ask")
async def ask_question(request):
    # Your existing logic
    pass
```

## 🔧 Configuration Options

### Database Optimization

```python
# In district_postgres_tools.py, configure connection pooling:
postgres_tools = DistrictAwarePostgresTools(
    host="your-host",
    port=5432,
    connection_pool_size=10,  # Adjust based on load
    max_overflow=20,
    schema="public"
)
```

### Model Selection

The system uses **GPT-4o-mini** by default for optimal cost/performance. To change:

```python
# In educational_agent.py
self.agent = Agent(
    model=OpenAIChat(id="gpt-4o"),  # For higher accuracy
    # or
    model=OpenAIChat(id="gpt-3.5-turbo"),  # For lower cost
)
```

### District Security

```python
# Enable additional security features
postgres_tools = DistrictAwarePostgresTools(
    district_id=district_id,
    enable_row_level_security=True,
    query_timeout=30,  # seconds
    max_results=1000,
    audit_logging=True
)
```

## 📋 Database Schema

The system expects these core tables with `district_id` columns:

- `districts` - District information
- `software` - Software catalog with district assignments  
- `users` - User profiles (anonymized)
- `usage_data` - Software usage tracking
- `mv_software_usage_summary` - Materialized view for performance
- `mv_daily_usage_trends` - Materialized view for trends

All queries are automatically filtered by the user's `district_id`.

## 🔍 Monitoring & Debugging

### Health Monitoring
```bash
# Check system health
curl http://localhost:8000/health

# Monitor logs
docker-compose logs -f analytics-api
```

### SQL Query Debugging
The API returns the actual SQL queries executed for transparency:

```json
{
  "success": true,
  "html_response": "...",
  "sql_executed": "SELECT COUNT(*) FROM software WHERE district_id = 'DIST001'"
}
```

### Performance Optimization
- Monitor materialized view refresh frequency
- Use database connection pooling
- Implement query result caching
- Add database query timeouts

## 🤝 Integration Examples

### React Frontend Integration

```javascript
// React component example
const AnalyticsComponent = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');
  
  const askQuestion = async () => {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: query,
        district_id: 'DIST001'
      })
    });
    
    const data = await response.json();
    setResult(data.html_response);
  };
  
  return (
    <div>
      <input 
        value={query} 
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask about your district's software usage..."
      />
      <button onClick={askQuestion}>Ask</button>
      <div dangerouslySetInnerHTML={{__html: result}} />
    </div>
  );
};
```

### Python SDK Integration

```python
import requests

class AnalyticsClient:
    def __init__(self, base_url, district_id):
        self.base_url = base_url
        self.district_id = district_id
    
    def ask_question(self, message):
        response = requests.post(f"{self.base_url}/api/ask", json={
            "message": message,
            "district_id": self.district_id
        })
        return response.json()
    
    def get_dashboard(self):
        response = requests.get(f"{self.base_url}/api/dashboard/{self.district_id}")
        return response.json()

# Usage
client = AnalyticsClient("http://localhost:8000", "DIST001")
result = client.ask_question("What software needs attention?")
print(result['html_response'])
```

## 🛡️ Security Best Practices

1. **Database Access:**
   - Use read-only database users
   - Enable PostgreSQL row-level security
   - Regularly rotate database credentials

2. **API Security:**
   - Implement JWT authentication for production
   - Add rate limiting to prevent abuse
   - Validate all district_id inputs

3. **AI Safety:**
   - Monitor for prompt injection attempts
   - Log all queries for audit purposes
   - Implement query complexity limits

## 📞 Support & Troubleshooting

### Common Issues

**Connection Errors:**
```bash
# Check database connectivity
docker-compose exec postgres psql -U analytics_user -d analytics_db -c "SELECT 1;"
```

**OpenAI API Issues:**
```bash
# Verify API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Performance Issues:**
- Refresh materialized views: `REFRESH MATERIALIZED VIEW mv_software_usage_summary;`
- Check database connection pool settings
- Monitor memory usage of the application

### Getting Help

- Check the `/health` endpoint for system status
- Review logs with `docker-compose logs analytics-api`
- Verify environment variables are properly set
- Ensure PostgreSQL has the required schema and data

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

---

**Built with ❤️ using Phidata, FastAPI, and PostgreSQL**
