from app.image_processor import detect_objects, generate_room_description
from app.llm_suggester import get_makeover_plan

def image_to_makeover(image_path: str, budget: int, style: str = "Any") -> dict:
    try:
        print("[DEBUG] Step 1: Starting object detection...")
        items = detect_objects(image_path)
        print("[DEBUG] Step 2: Detected items:", items)

        room_description = generate_room_description(items)
        print("[DEBUG] Step 3: Room description:", room_description)

        llm_output = get_makeover_plan(room_description, budget, style)
        
        # Respect error responses from LLM helper
        if llm_output.get("status") == "error":
            raise ValueError(f"LLM error: {llm_output.get('message')}")
        
        # Check if LLM returned anything
        if not llm_output.get("raw_output"):
            raise ValueError("LLM returned empty response")

        print("[DEBUG] Step 4: Got LLM response")

        return {
            "status": "success",
            "room_description": room_description,
            "detected_items": items,
            "llm_response": llm_output["raw_output"],
            "image_url": image_path.replace("\\", "/")  # Ensure compatibility for Flask
        }

    except Exception as e:
        print("[ERROR] Pipeline failed:", str(e))
        return {
            "status": "error",
            "message": f"Pipeline error: {str(e)}"
        }
