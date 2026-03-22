from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Recipe:
    title: str = ""
    source_url: str = ""
    image_url: str = ""
    ingredients: list[str] = field(default_factory=list)
    prep_minutes: Optional[int] = None
    cook_minutes: Optional[int] = None
    total_minutes: Optional[int] = None
    calories_per_serving: Optional[int] = None
    servings: Optional[int] = None
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Recipe:
        return cls(
            title=d.get("title", ""),
            source_url=d.get("source_url", ""),
            image_url=d.get("image_url", ""),
            ingredients=d.get("ingredients", []),
            prep_minutes=d.get("prep_minutes"),
            cook_minutes=d.get("cook_minutes"),
            total_minutes=d.get("total_minutes"),
            calories_per_serving=d.get("calories_per_serving"),
            servings=d.get("servings"),
            description=d.get("description", ""),
        )


@dataclass
class EatOutMeal:
    name: str = ""
    notes: str = ""
    estimated_calories: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EatOutMeal:
        return cls(
            name=d.get("name", ""),
            notes=d.get("notes", ""),
            estimated_calories=d.get("estimated_calories"),
        )


@dataclass
class DinnerSlot:
    day: str = ""
    meal_type: str = "recipe"  # "recipe" or "eat_out"
    recipe: Optional[Recipe] = None
    eat_out: Optional[EatOutMeal] = None
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "meal_type": self.meal_type,
            "recipe": self.recipe.to_dict() if self.recipe else None,
            "eat_out": self.eat_out.to_dict() if self.eat_out else None,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DinnerSlot:
        recipe = Recipe.from_dict(d["recipe"]) if d.get("recipe") else None
        eat_out = EatOutMeal.from_dict(d["eat_out"]) if d.get("eat_out") else None
        return cls(
            day=d.get("day", ""),
            meal_type=d.get("meal_type", "recipe"),
            recipe=recipe,
            eat_out=eat_out,
            note=d.get("note", ""),
        )

    @property
    def display_name(self) -> str:
        if self.meal_type == "eat_out" and self.eat_out:
            return self.eat_out.name or "Eating out"
        if self.recipe:
            return self.recipe.title
        return ""

    @property
    def is_planned(self) -> bool:
        if self.meal_type == "eat_out" and self.eat_out and self.eat_out.name:
            return True
        if self.meal_type == "recipe" and self.recipe and self.recipe.title:
            return True
        return False

    @property
    def calories(self) -> Optional[int]:
        if self.meal_type == "eat_out" and self.eat_out:
            return self.eat_out.estimated_calories
        if self.recipe:
            return self.recipe.calories_per_serving
        return None


@dataclass
class GroceryItem:
    name: str = ""
    context: str = ""
    checked: bool = False
    manual: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> GroceryItem:
        return cls(
            name=d.get("name", ""),
            context=d.get("context", ""),
            checked=d.get("checked", False),
            manual=d.get("manual", False),
        )


@dataclass
class AppState:
    dinners: dict[str, DinnerSlot] = field(default_factory=dict)
    grocery: list[GroceryItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dinners": {k: v.to_dict() for k, v in self.dinners.items()},
            "grocery": [g.to_dict() for g in self.grocery],
        }

    @classmethod
    def from_dict(cls, d: dict) -> AppState:
        dinners = {}
        for k, v in d.get("dinners", {}).items():
            dinners[k] = DinnerSlot.from_dict(v)
        grocery = [GroceryItem.from_dict(g) for g in d.get("grocery", [])]
        return cls(dinners=dinners, grocery=grocery)
