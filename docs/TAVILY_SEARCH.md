# Tavily Web Search Integration

## Overview

The Tavily web search integration enables your voice assistant to search the web for real-time information and answer questions that require current data like weather, news, documentation, and general facts.

## Features

- **Real-time Web Search**: Search for current information using Tavily's powerful search API
- **LLM Synthesis**: Search results are automatically synthesized into brief, natural spoken responses
- **Graceful Error Handling**: Works seamlessly even when disabled or API key is missing
- **Simple Configuration**: Just add your Tavily API key and you're ready to go

## Configuration

### 1. Get a Tavily API Key

1. Visit [https://tavily.com](https://tavily.com) and sign up for a free account
2. Get 1,000 free API credits per month (no credit card required)
3. Copy your API key from the dashboard

### 2. Configure the Assistant

You can provide the API key in two ways:

**Option A: Environment Variable (Recommended)**
```bash
# Add to your .env file or set in your shell
export TAVILY_API_KEY="tvly-YOUR_API_KEY_HERE"
```

**Option B: Configuration File**
```json
// In config.json
{
  "tavily_settings": {
    "enabled": true,
    "api_key": "tvly-YOUR_API_KEY_HERE"
  }
}
```

### 3. Enable/Disable

To disable web search without removing the API key:
```json
{
  "tavily_settings": {
    "enabled": false,
    "api_key": "tvly-YOUR_API_KEY_HERE"
  }
}
```

## Usage Examples

### Voice Commands

Once configured, simply ask questions that require web search:

- **Weather**: "What's the weather in Paris today?"
- **News**: "What's happening in the news?"
- **Documentation**: "Search for Python asyncio documentation"
- **General Questions**: "What is the capital of Australia?"
- **Information Lookup**: "Find information about the Eiffel Tower"

### How It Works (Multi-Step Agentic Workflow)

The web search follows a multi-step agentic pattern similar to screenshot analysis:

1. User asks a question requiring real-time information
2. The LLM recognizes this and calls the `web_search` tool with the query
3. **Tavily searches the web** and returns relevant results (top 5)
4. **The tool itself calls the LLM** to synthesize the search results into a concise answer
5. The synthesized answer is returned as feedback
6. The answer is spoken to the user via TTS

This is a **multi-step workflow** where the tool performs multiple operations:
- Step 1: Web search (Tavily API)
- Step 2: Result synthesis (LLM call within the tool)
- Step 3: Return spoken answer

This pattern ensures the user gets a coherent, synthesized answer rather than raw search results.

## Testing

A comprehensive test suite is available:

```bash
python -m src.test_tavily
```

The tests cover:
- Basic search functionality
- Error handling (empty queries, invalid API keys)
- Registry integration
- Configuration validation
- Result format verification

## Technical Details

### Files Modified
- `requirements.txt` - Added tavily-python package
- `src/config/settings.py` - Added TavilySettings configuration
- `src/llm/prompts.py` - Added web search rules and tool definition
- `src/tools/registry.py` - Added Tavily manager initialization and execution handler
- `config.template.json` - Added tavily_settings section
- `config.json` - Added tavily_settings section

### Files Created
- `src/tools/tavily_manager.py` - Core Tavily search logic
- `src/test_tavily.py` - Comprehensive test suite
- `docs/TAVILY_SEARCH.md` - This documentation

### Architecture (Multi-Step Agentic Workflow)

```
User Voice Question
    ↓
Wake Word Detection
    ↓
Transcription (Groq Whisper)
    ↓
LLM Processing (recognizes need for web search)
    ↓
web_search tool called with query
    ↓
┌─── TavilyManager Multi-Step Workflow ───┐
│                                          │
│  Step 1: Tavily Search API               │
│    ↓                                     │
│  Search results (top 5)                  │
│    ↓                                     │
│  Step 2: Format results for LLM          │
│    ↓                                     │
│  Step 3: Call LLM for synthesis          │
│    ↓                                     │
│  Synthesized answer (1-3 sentences)      │
│                                          │
└──────────────────────────────────────────┘
    ↓
Answer returned as feedback
    ↓
TTS speaks the answer to user
```

**Key Difference from Traditional Tools:**
- Traditional: Tool returns data → LLM processes → speak_response called
- Web Search: Tool performs search **AND** synthesis internally → returns ready-to-speak answer

This multi-step agentic pattern is also used by the screenshot analysis tool.

## Error Handling

The implementation handles various error conditions gracefully:

- **No API Key**: Returns "Web search is not available"
- **Empty Query**: Returns "I need a search query"
- **Network Errors**: Returns "Search failed" with error details
- **Rate Limits**: Tavily error message passed through
- **Too Long Query**: Tavily enforces 400 character max

## Limitations

- **Query Length**: Maximum 400 characters per query
- **Rate Limits**: Free tier provides 1,000 searches per month
- **Search Parameters**: Currently uses basic search only (can be extended later)

## Future Enhancements

Possible future improvements:

1. **Advanced Search Options**: Add support for search_depth, max_results, include_domains
2. **Caching**: Cache recent search results to save API credits
3. **Search History**: Track and display recent searches
4. **Domain Filtering**: Allow user to prefer certain sources
5. **Image Search**: Add support for image search results

## Troubleshooting

### "Web search is not available"
- Check that `tavily_settings.enabled` is `true` in config.json
- Verify your API key is set (environment variable or config file)
- Run tests to validate configuration: `python -m src.test_tavily`

### "Search failed: Unauthorized"
- Your API key is invalid or missing
- Get a new API key from https://tavily.com

### "Search failed: Query is too long"
- Queries must be under 400 characters
- The LLM should handle this automatically, but you can rephrase if needed

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Run the test suite: `python -m src.test_tavily`
3. Review this documentation
4. Check Tavily's documentation: https://docs.tavily.com

## Credits

- **Tavily**: https://tavily.com - Powerful search API for LLMs
- **Implementation**: Following the established patterns from ADDING_NEW_TOOLS.md

