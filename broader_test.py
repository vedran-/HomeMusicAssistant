from src.config.settings import load_settings
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools

# Test multiple cases
settings = load_settings()
llm_client = LiteLLMClient(settings)
system_prompt = get_system_prompt()
available_tools = get_available_tools()

test_cases = [
    "play Magazines",
    "play jazz", 
    "play The Beatles",
    "play rock music"
]

success_count = 0

for test_case in test_cases:
    print(f"\nTesting: '{test_case}'")
    try:
        result = llm_client.process_transcript(test_case, system_prompt, available_tools)
        
        if result and result.get('tool_name') == 'play_music':
            search_term = result['parameters'].get('search_term', '')
            print(f"✅ SUCCESS: play_music with search_term='{search_term}'")
            success_count += 1
        else:
            print(f"❌ FAILED: Got {result}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print(f"\n📊 Overall: {success_count}/{len(test_cases)} tests passed")
if success_count == len(test_cases):
    print("🎉 All core play commands now work correctly!") 