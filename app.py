import logging

import gradio as gr
import pandas as pd

from database import(
    run_ddl,
    get_meal_data,
    save_meal_data
)
from food_analyzer import analyze_food
from models import Fooditem

logger = logging.getLogger(__name__)

# create tables if it does not exist
run_ddl()

def analyze_image(image_path):
    if not image_path:
        return None, pd.DataFrame(), "upload image first"

    try:
        result = analyze_food(image_path)
        foods = [food.model_dump() for food in result.foods]
        if not foods:
            return None, pd.DataFrame(), "No food identified, upload image again, or try another image"

        dataframe = pd.DataFrame(foods)
        return {
            "foods": foods,
            "notes": result.notes,
        }, dataframe, "Analysis complete"
    except Exception as e:
        logger.exception("analyze_image failed")
        return None, pd.DataFrame(), f"Analysis failed: {e}"

def save_reviewed_meal_info(data, edited_foods):
    if not data or not data.get("foods"):
        return "No History, lets start with analyzing a food"

    if edited_foods is None or len(edited_foods) == 0:
        return "No food items to save"


    try:
        foods = [
            Fooditem.model_validate(row)
            for row in edited_foods.to_dict(orient="records")
        ]
        meal_id = save_meal_data(foods, data.get("notes", ""))
        return "Meal successfully saved, Meal_ID: {}".format(meal_id)
    except Exception as e:
        return f"Meal info save failed: {e}"

def show_meal_history():
    rows = get_meal_data()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(dict(row) for row in rows)


# building gradio UI
with gr.Blocks(title="Visual Food Assistant") as ui:
    gr.Markdown("# Visual Food and Meal Planning Assistant")
    gr.Markdown("Upload an image and get the nutritional information")

    analysis_state = gr.State(None)

    with gr.Tab("Analyze Meal"):
        image_input=gr.Image(
            type="filepath",
            label="Upload your meal image",
        )
        analyze_button=gr.Button("Analyze Meal", variant="primary")

        food_table= gr.DataFrame(
            headers=[
                "food_name",
                "quantity_g",
                "calories_g",
                "protein_g",
                "carbs_g",
                "fat_g",
            ],
            datatype=[
                "str", "number", "number",
                "number", "number", "number",
            ],
            interactive=True,
            label="Review and edit nutrition estimates",
        )

        save_button=gr.Button("Save Reviewed Meal Info")
        status=gr.Textbox(
        label="Status",
        interactive=False,
        )

        analyze_button.click(fn=analyze_image, inputs=image_input, outputs=[analysis_state, food_table, status])
        save_button.click(fn=save_reviewed_meal_info, inputs=[analysis_state, food_table], outputs=status)

    with gr.Tab("Meal History"):
        history_button=gr.Button("Refresh history")
        history_table=gr.DataFrame(
            label="Previously saved meals",
            interactive=False,
        )
        history_button.click(fn=show_meal_history, outputs=history_table)

if __name__ == "__main__":
    show_meal_history()
    ui.launch()