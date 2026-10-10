from typing import List
from pydantic import BaseModel, Field


class Fooditem(BaseModel):
    food_name: str
    quantity_g: float = Field(gt=0)
    calories_g: float = Field(gt=0)
    proteins_g: float = Field(gt=0)
    carbs_g: float = Field(gt=0)
    fats_g: float = Field(gt=0)

class FoodAnalysis(BaseModel):
    foods: List[Fooditem]
    notes: str = ""