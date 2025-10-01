import streamlit as st
import os
import tempfile
import json
import re
from urllib.parse import quote
from io import BytesIO
from xhtml2pdf import pisa
from app.pipeline import image_to_makeover

# Page setup
st.set_page_config(page_title="RoomMakeover.AI", layout="centered")
st.title("🏡 RoomMakeover.AI")
st.markdown("Upload a room image and get a personalized makeover plan powered by **YOLOv8 + Gemini 1.5 Flash**.")

# Upload image
uploaded_file = st.file_uploader("📤 Upload a room image (.jpg or .jpeg)", type=["jpg", "jpeg"])

# Budget input
budget = st.number_input("💸 Enter your budget (₹)", min_value=500, max_value=10000, value=1500, step=100)

# Style input
style = st.selectbox("🎨 Choose a preferred style", ["Any", "Modern", "Minimalist", "Cozy", "Boho", "Industrial"])

# Submit button
submit = st.button("✨ Suggest Makeover", key="makeover_button")

if submit:
    if not uploaded_file:
        st.warning("⚠️ Please upload an image first.")
    else:
        with st.spinner("Processing your room image..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            result = image_to_makeover(tmp_path, budget, style)
            os.remove(tmp_path)

        # Room Description
        st.subheader("🧩 Room Description")
        room_description = result.get("room_description", "No description generated.")
        st.write(room_description)

        # Gemini Output
        llm_resp = result.get("llm_response", {})
        if llm_resp.get("status") == "success":
            st.subheader("🎨 Makeover Suggestion")
            raw_output = llm_resp.get("raw_output", "")
            cleaned = re.sub(r"```json|```", "", raw_output).strip()

            try:
                parsed = json.loads(cleaned)

                st.markdown("#### 🪑 Items to Add:")
                html_items = ""
                for item in parsed.get("items", []):
                    name = item.get("name") or item.get("item") or "Unnamed Item"
                    price = item.get("price", "N/A")
                    desc = item.get("description", "")
                    link = item.get("link", "")

                    # Show on web interface
                    st.markdown(f"**🛋️ {name}** — ₹{price}")
                    st.markdown(f"_{desc}_")

                    if link:
                        st.markdown(
                            f'<a href="{link}" target="_blank">🔗 Shop on Amazon</a>',
                            unsafe_allow_html=True
                        )
                    else:
                        search_query = quote(name)
                        amazon_url = f"https://www.amazon.in/s?k={search_query}"
                        st.markdown(
                            f'<a href="{amazon_url}" target="_blank">🔍 Search on Amazon</a>',
                            unsafe_allow_html=True
                        )

                    st.markdown("---")

                    # For PDF
                    html_items += f"<li><b>{name}</b> — ₹{price}<br><i>{desc}</i></li><br>"

                total_price = parsed.get("total_price", "N/A")
                notes = parsed.get("notes", "")

                st.markdown(f"#### 💰 Total Price: ₹{total_price}")
                st.markdown("#### 📝 Notes:")
                st.write(notes)

                # PDF Generation
                html_content = f"""
                <h2>RoomMakeover.AI - Makeover Plan</h2>
                <h4>🧩 Room Description</h4>
                <p>{room_description}</p>

                <h4>🪑 Items to Add</h4>
                <ul>{html_items}</ul>

                <h4>💰 Total Price</h4>
                <p>₹{total_price}</p>

                <h4>📝 Notes</h4>
                <p>{notes}</p>
                """

                pdf_buffer = BytesIO()
                pisa.CreatePDF(html_content, dest=pdf_buffer)
                pdf_buffer.seek(0)

                st.download_button(
                    label="📄 Download Makeover Plan as PDF",
                    data=pdf_buffer,
                    file_name="room_makeover_plan.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ JSON parsing failed: {e}")
                st.code(raw_output)
        else:
            st.error(f"❌ Gemini Error: {llm_resp.get('message', 'Unknown error')}")
