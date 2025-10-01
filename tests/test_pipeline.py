# tests/test_pipeline.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import image_to_makeover

image_path = "sample_data/room.jpeg"
budget = 1500
style = "Modern cozy"

result = image_to_makeover(image_path, budget, style)

print("\n🧩 Room Description:")
print(result.get("room_description", "N/A"))

if result.get("status") == "success":
    print("\n🎨 Gemini Decor Suggestion:")
    print(result.get("llm_response", "No response"))
else:
    print("\n❌ Error:")
    print(result.get("message", "Unknown error"))
