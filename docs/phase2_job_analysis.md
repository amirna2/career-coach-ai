# Phase 2: Job Analysis Implementation Plan

## Overview
Add job analysis capabilities to the Career Coach AI using a sub-agent architecture.

## Current Status
✅ Phase 1: Basic coaching with document context complete
✅ Job Discovery: `search_jobs()` tool integrated and ready for testing

## Phase 2 Goals
- User provides job URL or requests job analysis
- JobAnalysisAgent fetches job content and analyzes against profile
- Coach receives structured analysis and provides strategic recommendations

## Architecture: Sub-Agent Approach

### Components
1. **CareerCoach** (main agent)
   - Handles conversation and strategy
   - Delegates job analysis to JobAnalysisAgent
   - Provides actionable recommendations

2. **JobAnalysisAgent** (sub-agent)
   - Fetches job description from URL
   - Extracts structured job requirements
   - Analyzes match against user profile
   - Returns structured analysis

### Implementation Steps

**Step 1: Test Job Discovery**
- Test current `search_jobs()` through conversation
- Example: "Can you find Senior Software Engineering Jobs?"

**Step 2: Build JobAnalysisAgent**
- Create sub-agent for job content analysis
- Implement job content fetching and matching

**Step 3: Integrate Sub-Agent**
- Connect JobAnalysisAgent to CareerCoach via handoff
- Test complete analysis workflow

## Success Criteria
✅ Job discovery works through conversation
✅ JobAnalysisAgent analyzes job URLs effectively
✅ Coach provides strategic guidance based on analysis