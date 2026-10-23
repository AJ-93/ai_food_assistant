import logging
from datetime import date

import gradio as gr
import pandas as pd
import plotly.express as px

from database import(
    run_ddl,
    get_meal_data,
    save_meal_data,
    get_daily_nutrition,
    get_daily_trend,
    get_meals_for_date
)
from food_analyzer import analyze_food
from models import Fooditem

logger = logging.getLogger(__name__)

# create tables if it does not exist
run_ddl()

FOOD_COLUMNS = [
    "food_name",
    "quantity_g",
    "calories_g",
    "protein_g",
    "carbs_g",
    "fat_g",
]


def run_analysis(input_data, input_type, empty_message):
    """Shared by image and voice: returns (state, table, status)."""
    if not input_data:
        return None, pd.DataFrame(columns=FOOD_COLUMNS), empty_message

    try:
        result = analyze_food(input_data, input_type=input_type)
        foods = [food.model_dump() for food in result.foods]
        if not foods:
            return (
                None,
                pd.DataFrame(columns=FOOD_COLUMNS),
                "No food identified, try again with another image or recording",
            )

        dataframe = pd.DataFrame(foods, columns=FOOD_COLUMNS)
        return {
            "foods": foods,
            "notes": result.notes,
        }, dataframe, "Analysis complete"
    except Exception as e:
        logger.exception("analysis failed (%s)", input_type)
        return None, pd.DataFrame(columns=FOOD_COLUMNS), f"Analysis failed: {e}"


def analyze_image(image_path):
    return run_analysis(image_path, "image", "upload image first")


def analyze_voice(audio_path):
    return run_analysis(audio_path, "voice", "record your meal first")

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

def dashboard_refresh(target_date, period, calorie_goal, protein_goal, carbs_goal, fats_goal):
    try:
        date.fromisoformat(target_date)
    except Exception as e:
        raise gr.Error("Enter a valid date in YYYY-MM-DD format")

    total_nutrition = get_daily_nutrition(target_date)

    days = int(period)
    trend = get_daily_trend(days)

    fig = px.line(
        trend,
        x="day",
        y="calories",
        markers=True,
        title= "Daily Nutrition for last {days} days".format(days=days),
        labels={
            "day": "date",
            "calories": "calories (kcal)",
        }
    )

    fig.update_layout(hovermode="x unified")

    meals = get_meals_for_date(target_date)

    return (
        f"{total_nutrition['calories']:.0f} kcal",
        f"{total_nutrition['protein_g']:.1f} g",
        f"{total_nutrition['carbs_g']:.1f} g",
        f"{total_nutrition['fat_g']:.1f} g",
        fig,
        meals,
    )

# building gradio UI
with gr.Blocks(title="Visual Food Assistant") as ui:
    gr.Markdown("# Visual Food and Meal Planning Assistant")
    gr.Markdown("Upload an image or describe the food and get the nutritional information")

    analysis_state = gr.State(None)

    with gr.Tab("Analyze Meal"):
        gr.Markdown(
            "You can choose whether to upload an image or describe the food to get the nutritional information",
        )
        with gr.Tabs():
            with gr.Tab("Image"):
                image_input = gr.Image(
                    type="filepath",
                    label="Upload your meal image",
                )
                analyze_button = gr.Button("Analyze Meal", variant="primary")

            with gr.Tab("Voice"):
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="Record your meal",
                )
                analyze_voice_button = gr.Button("Analyze Recording", variant="primary")

        # one shared table, save button and status for both inputs
        food_table = gr.DataFrame(
            headers=FOOD_COLUMNS,
            datatype=[
                "str", "number", "number",
                "number", "number", "number",
            ],
            interactive=True,
            label="Review and edit nutrition estimates",
        )

        save_button = gr.Button("Save Reviewed Meal Info")
        status = gr.Textbox(
            label="Status",
            interactive=False,
        )

        shared_outputs = [analysis_state, food_table, status]
        analyze_button.click(fn=analyze_image, inputs=image_input, outputs=shared_outputs)
        analyze_voice_button.click(fn=analyze_voice, inputs=audio_input, outputs=shared_outputs)
        save_button.click(fn=save_reviewed_meal_info, inputs=[analysis_state, food_table], outputs=status)

    with gr.Tab("Meal History"):
        history_button=gr.Button("Refresh history")
        history_table=gr.DataFrame(
            label="Previously saved meals",
            interactive=False,
        )
        history_button.click(fn=show_meal_history, outputs=history_table)

    with gr.Tab("Dashboard"):
        gr.Markdown("# Nutrition Dashboard")
        gr.Markdown("Review your daily nutrition")

        with gr.Row():
            dashboard_date = gr.Textbox(
                label= "Date",
                value=str(date.today()),
                placeholder="Enter a date in YYYY-MM-DD format",
            )
            trend_period = gr.Dropdown(
                choices=["7","30"],
                value="7",
                label="trend period",
            )

    gr.Markdown("### Daily nutrition goals")

    with gr.Row():
        calorie_goal = gr.Number(label="Calories (kcal)", value=2000, minimum=1)
        protein_goal = gr.Number(label="Protein (g)", value=120, minimum=1)
        carbs_goal = gr.Number(label="Carbohydrates (g)", value=250, minimum=1)
        fat_goal = gr.Number(label="Fat (g)", value=65, minimum=1)

    refresh_button = gr.Button("Refresh dashboard", variant="primary")

    with gr.Row():
        calories_output = gr.Textbox(label="Daily calories", interactive=False)
        protein_output = gr.Textbox(label="Protein", interactive=False)
        carbs_output = gr.Textbox(label="Carbohydrates", interactive=False)
        fat_output = gr.Textbox(label="Fat", interactive=False)

    calories_chart = gr.Plot(label="Calorie trend")

    gr.Markdown("### Meals logged on this date")
    meal_history = gr.Dataframe(
        headers=[
            "meal_id",
            "logged_at",
            "notes",
            "foods",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
        ],
        interactive=False,
        label="Meal history",
    )

    dashboard_outputs = [
        calories_output,
        protein_output,
        carbs_output,
        fat_output,
        calories_chart,
        meal_history,
    ]

    refresh_button.click(
        fn=dashboard_refresh,
        inputs=[
            dashboard_date,
            trend_period,
            calorie_goal,
            protein_goal,
            carbs_goal,
            fat_goal,
        ],
        outputs=dashboard_outputs,
    )

    # Load dashboard data when the app starts.
    ui.load(
        fn=dashboard_refresh,
        inputs=[
            dashboard_date,
            trend_period,
            calorie_goal,
            protein_goal,
            carbs_goal,
            fat_goal,
        ],
        outputs=dashboard_outputs,
    )

if __name__ == "__main__":
    show_meal_history()
    ui.launch()
