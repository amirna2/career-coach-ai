# AI-Powered Job Filtering Implementation Plan

## Problem Statement

Current job search results include irrelevant positions despite exclusion filters because:

1. **Search engines don't understand variations**: `-frontend` doesn't exclude "React Developer", "UI Engineer", "JavaScript Engineer"
2. **Keyword matching is insufficient**: Context matters (Node.js backend vs React frontend)
3. **Manual exclusion lists are unmaintainable**: Infinite variations, new frameworks, different industries

## Solution: AI Filtering Agent using Agents SDK

Use the Agents SDK `as_tool()` pattern to create an intelligent job filtering agent that understands semantic meaning.

## Architecture

### 1. JobFilteringAgent
```python
from agents import Agent

job_filter_agent = Agent(
    name="JobFilter",
    instructions="""
    You are an expert at analyzing job postings and determining relevance.

    Given:
    - Raw job search results (titles + descriptions)
    - User requirements
    - User exclusions

    Filter jobs that truly match user needs, understanding:
    - Context and semantic meaning
    - Technology stack implications
    - Role responsibilities
    - Industry nuances
    """,
    model="gpt-4o-mini"  # Fast + cheap for filtering
)
```

### 2. Convert to Tool
```python
filter_jobs_tool = job_filter_agent.as_tool(
    tool_name="filter_jobs_intelligently",
    tool_description="Semantically filter job results based on user requirements and exclusions"
)
```

### 3. Integration in search_jobs()
```python
@function_tool
def search_jobs(title: str, expression: str = "", backend: str = "google", limit: int = 10) -> str:
    # ... existing search logic ...

    # Get raw results from DDGS
    raw_results = ddgs.text(query, max_results=limit*2)  # Get extra for filtering

    # Apply AI filtering
    filtered_results = filter_jobs_tool(
        job_results=format_raw_results(raw_results),
        user_requirements=f"Title: {title}, Expression: {expression}",
        user_exclusions=extract_exclusions_from_expression(expression)
    )

    # ... process filtered results ...
```

## Implementation Steps

### Phase 1: Core Agent
- [ ] Create JobFilteringAgent with comprehensive system prompt
- [ ] Test agent behavior with sample job data
- [ ] Convert agent to tool using `as_tool()`

### Phase 2: Integration
- [ ] Modify search_jobs() to collect raw results
- [ ] Add AI filtering step before validation
- [ ] Format filtered results for final output

### Phase 3: Optimization
- [ ] Fine-tune filtering prompts based on results
- [ ] Add caching to avoid re-filtering similar jobs
- [ ] Monitor AI filtering accuracy and costs

## Benefits

1. **Semantic Understanding**: Knows "React Developer" = frontend regardless of keywords
2. **Context Awareness**: Distinguishes Node.js backend from React frontend
3. **Natural Language**: Handles any exclusion ("no customer-facing", "avoid startups")
4. **Zero Maintenance**: No keyword lists to maintain
5. **Learns**: Gets better with feedback and examples

## Technical Details

### Input Format to Filtering Agent
```json
{
  "jobs": [
    {
      "title": "Senior Software Engineer",
      "company": "TechCorp",
      "description": "We are looking for...",
      "url": "https://..."
    }
  ],
  "requirements": "Senior software engineer, remote, embedded systems",
  "exclusions": "frontend, fullstack, customer-facing roles"
}
```

### Expected Output
```json
{
  "filtered_jobs": [
    {
      "title": "Senior Software Engineer",
      "company": "TechCorp",
      "url": "https://...",
      "relevance_reason": "Matches embedded systems requirement, clearly backend-focused role"
    }
  ],
  "removed_count": 12,
  "removal_reasons": ["7 frontend-focused", "3 fullstack", "2 customer-facing"]
}
```

## Cost Estimation

- **Model**: gpt-4o-mini (~$0.00015/1K tokens)
- **Input**: ~500 tokens per filtering call (job descriptions)
- **Expected cost**: <$0.01 per job search
- **ROI**: Massive time savings from cleaner results

## Future Enhancements

1. **User Feedback Loop**: Learn from user job selections
2. **Industry Specialization**: Different filtering for different domains
3. **Company Intelligence**: Factor in company culture, size, stage
4. **Salary Analysis**: Filter based on compensation expectations

## Notes

- Keep as separate agent to maintain modularity
- Use fast model (gpt-4o-mini) to minimize latency
- Consider caching for repeated similar queries
- Monitor token usage and optimize prompts

---

**Status**: Planning Phase
**Next Steps**: Implement JobFilteringAgent and test with sample data