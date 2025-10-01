import os
import sys
import json
import shutil
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory
from werkzeug.utils import secure_filename

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app.pipeline import image_to_makeover

# Folder paths
UPLOAD_FOLDER = os.path.join('static', 'uploads')
OUTPUT_FOLDER = os.path.join('static', 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Flask app setup
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'image' not in request.files:
            return render_template('index.html', error="No image uploaded")

        image = request.files['image']
        budget = request.form.get('budget')
        style = request.form.get('style', 'Any')

        if not budget or not budget.isdigit():
            return render_template('index.html', error="Invalid or missing budget")

        # Generate safe + unique filename
        filename = secure_filename(image.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        saved_filename = f"{timestamp}_{filename}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        image.save(image_path)

        # Create a working copy to avoid auto-reload conflicts
        working_image_path = image_path.replace(".jpeg", "_working.jpeg")
        shutil.copy(image_path, working_image_path)

        # Call image to makeover pipeline
        result = image_to_makeover(working_image_path, int(budget), style)

        if result.get("status") == "error":
            return render_template('index.html', error=result.get("message"))

        # Parse LLM response safely
        llm_response = result.get("llm_response", "")
        if isinstance(llm_response, dict):
            raw_output = llm_response.get("raw_output", "")
        else:
            raw_output = llm_response

        # Debug: Print the raw output for debugging
        print(f"[DEBUG] Flask Raw Output: {raw_output[:200]}...")

        # Try to parse JSON, with fallback for non-JSON responses
        try:
            if not raw_output or raw_output.strip() == "":
                raise ValueError("Empty LLM response")
            
            # Try to extract JSON from the response if it's wrapped in markdown
            json_start = raw_output.find('{')
            json_end = raw_output.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = raw_output[json_start:json_end]
                parsed = json.loads(json_str)
            else:
                parsed = json.loads(raw_output)
            
            items = parsed.get("items", [])
            total_price = parsed.get("total_price", None)
            notes = parsed.get("notes", "")
            
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON Parse Error: {e}")
            # Fallback: create a simple response from the raw text
            items = [{"name": "LLM Response", "description": raw_output[:100] + "...", "price": 0, "link": ""}]
            total_price = 0
            notes = "Could not parse LLM response as JSON. Showing raw response."
        except Exception as e:
            print(f"[DEBUG] General Parse Error: {e}")
            return render_template('index.html', error=f"LLM output parsing failed: {e}")

        return render_template(
            'index.html',
            uploaded=True,
            image_url=f"/static/uploads/{saved_filename}",
            room_description=result.get("room_description"),
            suggestions=items,
            total_price=total_price,
            notes=notes,
            detected_items=result.get("detected_items", [])
        )

    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

