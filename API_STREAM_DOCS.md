# Streaming API Documentation

## POST /api/ask/stream

Real-time streaming endpoint for educational software analytics queries using Server-Sent Events (SSE).

---

## Overview

This endpoint provides **real-time streaming responses** in Markdown format, offering significantly faster perceived response times compared to the standard `/api/ask` endpoint which returns HTML.

### Benefits
- **Instant feedback**: Response starts streaming immediately after data fetch
- **Markdown format**: Lightweight, easy to render in any modern UI
- **Real-time chunks**: Content appears as it's generated
- **Same accuracy**: Uses the same optimized materialized views for data

---

## Request

### Endpoint
```
POST /api/ask/stream
```

### Headers
```
Content-Type: application/json
Origin: https://classsight.ai  (or other allowed origin)
```

### Body
```json
{
  "message": "string (required) - Natural language query",
  "district_id": "string (required) - District identifier"
}
```

### Example Request
```bash
curl -N -X POST "https://lumi.classsight.ai/api/ask/stream" \
  -H "Content-Type: application/json" \
  -H "Origin: https://classsight.ai" \
  -d '{
    "message": "Show me all the paid software list",
    "district_id": "3ef51192-1070-4090-908d-ef3ab03b4325"
  }'
```

---

## Response

### Content-Type
```
text/event-stream
```

### SSE Event Format
Each event follows the SSE specification:
```
data: {JSON object}\n\n
```

---

## Event Types

### 1. Metadata Event
Sent first, contains query analysis information.

```json
{
  "type": "metadata",
  "primary_intent": "software_investment",
  "best_mv": "mv_software_investment_summary",
  "mv_queries_count": 2,
  "data_fetch_time": 0.945
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"metadata"` |
| `primary_intent` | string | Detected query intent |
| `best_mv` | string | Materialized view used |
| `mv_queries_count` | number | Number of MV queries executed |
| `data_fetch_time` | number | Time to fetch data (seconds) |

### 2. Content Event
Sent multiple times, contains markdown content chunks.

```json
{
  "type": "content",
  "text": "## 📊 Paid Software List\n\n"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"content"` |
| `text` | string | Markdown content chunk |

### 3. Done Event
Sent last on successful completion.

```json
{
  "type": "done",
  "execution_time": 3.45,
  "mv_queries_count": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"done"` |
| `execution_time` | number | Total execution time (seconds) |
| `mv_queries_count` | number | Number of MV queries executed |

### 4. Error Event
Sent if an error occurs during processing.

```json
{
  "type": "error",
  "error": "Error message description",
  "execution_time": 1.23
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"error"` |
| `error` | string | Error message |
| `execution_time` | number | Time until error (seconds) |

---

## Client Implementation Examples

### JavaScript (Browser)

```javascript
async function streamAnalytics(message, districtId) {
  const response = await fetch('/api/ask/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      district_id: districtId
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let markdown = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        switch (data.type) {
          case 'metadata':
            console.log('Query intent:', data.primary_intent);
            break;
          case 'content':
            markdown += data.text;
            // Update UI with new content
            updateMarkdownDisplay(markdown);
            break;
          case 'done':
            console.log('Completed in', data.execution_time, 'seconds');
            break;
          case 'error':
            console.error('Error:', data.error);
            break;
        }
      }
    }
  }

  return markdown;
}
```

### JavaScript (EventSource - Alternative)

```javascript
// Note: EventSource only supports GET, so use fetch for POST
// This example shows the pattern if you convert to GET endpoint

const eventSource = new EventSource('/api/ask/stream?message=...&district_id=...');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'content') {
    appendToDisplay(data.text);
  } else if (data.type === 'done') {
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

### React Hook Example

```javascript
import { useState, useCallback } from 'react';

function useStreamingAnalytics() {
  const [markdown, setMarkdown] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState(null);

  const askQuestion = useCallback(async (message, districtId) => {
    setIsLoading(true);
    setMarkdown('');
    setError(null);

    try {
      const response = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, district_id: districtId })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'metadata') {
              setMetadata(data);
            } else if (data.type === 'content') {
              setMarkdown(prev => prev + data.text);
            } else if (data.type === 'error') {
              setError(data.error);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { markdown, isLoading, metadata, error, askQuestion };
}
```

### Python Client

```python
import requests
import json

def stream_analytics(message: str, district_id: str, base_url: str = "https://lumi.classsight.ai"):
    """Stream analytics response from the API."""

    response = requests.post(
        f"{base_url}/api/ask/stream",
        json={"message": message, "district_id": district_id},
        headers={"Origin": "https://classsight.ai"},
        stream=True
    )

    markdown_content = ""

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])

                if data['type'] == 'metadata':
                    print(f"Intent: {data['primary_intent']}")
                    print(f"MV Used: {data['best_mv']}")

                elif data['type'] == 'content':
                    markdown_content += data['text']
                    print(data['text'], end='', flush=True)

                elif data['type'] == 'done':
                    print(f"\n\nCompleted in {data['execution_time']:.2f}s")

                elif data['type'] == 'error':
                    print(f"Error: {data['error']}")

    return markdown_content


# Usage
if __name__ == "__main__":
    result = stream_analytics(
        message="Show me all the paid software list",
        district_id="3ef51192-1070-4090-908d-ef3ab03b4325"
    )
```

---

## Query Intent Types

The API automatically detects query intent and routes to the optimal materialized view:

| Intent | Description | Example Queries |
|--------|-------------|-----------------|
| `dashboard_overview` | General dashboard metrics | "Show me the dashboard", "Overview" |
| `software_usage` | Software usage analytics | "How is software being used?" |
| `software_roi` | ROI analysis | "What's the ROI on our software?" |
| `software_investment` | Investment/cost analysis | "Show paid software", "Software costs" |
| `user_analytics` | User behavior analysis | "User analytics", "How are users engaging?" |
| `student_analysis` | Student-specific data | "Student usage", "How are students using..." |
| `teacher_analysis` | Teacher-specific data | "Teacher engagement", "Teacher usage" |
| `unauthorized_software` | Security/compliance | "Unauthorized apps", "Unapproved software" |
| `school_analysis` | School-level comparison | "Compare schools", "School usage" |
| `usage_rankings` | Usage rankings | "Top software", "Most used apps" |
| `active_users` | Active user metrics | "Active users", "Who's using..." |

---

## Markdown Response Format

Responses are formatted in GitHub-flavored Markdown:

```markdown
## 📊 Software Analytics Summary

### Key Metrics
| Metric | Value |
|--------|-------|
| Total Software | 25 |
| Total Cost | $50,000 |
| Average ROI | 72% |

### 💡 Key Insights
> Your top-performing software is achieving 85% ROI

### Software List
| Name | Cost | ROI | Status |
|------|------|-----|--------|
| Software A | $10,000 | High | ✅ Active |
| Software B | $5,000 | Moderate | ⚠️ Review |

### ✅ Recommendations
1. Review underutilized software
2. Consider consolidation opportunities
```

---

## Error Handling

### HTTP Errors

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Missing or invalid parameters |
| 403 | Forbidden - Invalid origin or unauthorized |
| 500 | Internal Server Error |

### SSE Error Event
If an error occurs during streaming, an error event is sent:
```json
{
  "type": "error",
  "error": "Database connection failed",
  "execution_time": 0.5
}
```

---

## Performance Comparison

| Endpoint | Response Type | Typical Time | User Experience |
|----------|--------------|--------------|-----------------|
| `/api/ask` | HTML (complete) | 200+ seconds | Wait for full response |
| `/api/ask/stream` | Markdown (streaming) | 3-5 seconds to first chunk | See content immediately |

---

## CORS Configuration

Allowed origins:
- `https://classsight.ai`
- `https://www.classsight.ai`
- `https://swye360.ai`
- `https://www.swye360.ai`
- `https://preview--roi-bright-future.lovable.app`

---

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing rate limiting for production use.

---

## Changelog

### v2.1.0 (2026-01-16)
- Added `/api/ask/stream` endpoint with SSE support
- Markdown response format for faster rendering
- Real-time streaming using OpenAI streaming API
