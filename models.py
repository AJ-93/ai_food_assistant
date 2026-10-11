from typing import List
from pydantic import BaseModel, Field


class Fooditem(BaseModel):
    food_name: str
    quantity_g: float = Field(gt=0)
    calories_g: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)

class FoodAnalysis(BaseModel):
    foods: List[Fooditem]
    notes: str = ""
