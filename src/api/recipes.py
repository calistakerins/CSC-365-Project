import datetime
from fastapi import APIRouter, HTTPException
from enum import Enum
from src import database as db
from fastapi.params import Query
import sqlalchemy
from sqlalchemy import desc, func, select
from sqlalchemy import*
from fastapi import HTTPException, Body
from typing import Optional
from typing import List
from pydantic import BaseModel
from sqlalchemy.sql.sqltypes import Integer, String
from psycopg2.errors import UniqueViolation


router = APIRouter()



@router.get("/recipes/{recipe_id}", tags=["recipes"])
def get_recipe(recipe_id: int):
    """
    This endpoint returns a single recipe by its identifier. For each recipe
    it returns:
    * `recipe_id`: the internal id of the recipe. Can be used to query the
      `/recipes/{id}` endpoint.
    * `recipe_name`: The name of the recipe.
    * `cuisine`: The cuisine that the recipe is from.
    * `meal_type`: The meal type that the recipe is from (breakfast, lunch, dinner, etc).
    * `ingredients`: The listed ingredients and amounts that are needed to make the recipe.
    * `prep_time_mins`: The total time needed to prep the recipe in minutes.
    * `instructions`: The instructions needed to make the recipe.
    * `number_of_favorites`: The number of users that have favorited the recipe.

    """
    json = None

    recipe_stmt = sqlalchemy.select(db.recipes.c.recipe_id, 
                db.recipes.c.recipe_name, db.recipes.c.prep_time_mins, db.recipes.c.recipe_instructions, db.recipes.c.number_of_favorites).where(db.recipes.c.recipe_id == recipe_id)

    meal_type_stmt = sqlalchemy.select(db.meal_type.c.meal_type).select_from(db.meal_type.join(db.recipe_meal_types, db.meal_type.c.meal_type_id == db.recipe_meal_types.c.meal_type_id)).where(db.recipe_meal_types.c.recipe_id == recipe_id)
    
    cuisine_type_stmt = sqlalchemy.select(db.cuisine_type.c.cuisine_type).select_from(db.cuisine_type.join(db.recipe_cuisine_types, db.cuisine_type.c.cuisine_type_id == db.recipe_cuisine_types.c.cuisine_type_id)).where(db.recipe_cuisine_types.c.recipe_id == recipe_id)

    with db.engine.connect() as conn:
        recipe_result = conn.execute(recipe_stmt)
        meal_type_result = conn.execute(meal_type_stmt)
        cuisine_type_result = conn.execute(cuisine_type_stmt)
        meal_type = []
        cuisine_type = []
        for row in meal_type_result:
            meal_type.append(row.meal_type)
        for row in cuisine_type_result:
            cuisine_type.append(row.cuisine_type)
        for row in recipe_result:
            json = {
                "recipe_id": row.recipe_id,
                "recipe_name": row.recipe_name,
                "cuisine_type": cuisine_type,
                "meal_type": meal_type,
                "prep_time_mins": row.prep_time_mins,
                "instructions": row.recipe_instructions,
                "number_of_favorites": row.number_of_favorites,
            }

    if json is None:
            raise HTTPException(status_code=404, detail="Recipe not found.")

    return json



def get_meal_type(recipe_id: int):
    find_meal_types = sqlalchemy.select(
            db.meal_type.c.meal_type,
        ).select_from(db.meal_type.join(db.recipe_meal_types, db.meal_type.c.meal_type_id == db.recipe_meal_types.c.meal_type_id)).\
        where(db.recipe_meal_types.c.recipe_id == recipe_id)
    
    with db.engine.connect() as conn:
        meal_type_result = conn.execute(find_meal_types)
        if meal_type_result.rowcount == 0:
            raise HTTPException(status_code=404, detail="meal type not found")
        
        meal_types = []
        for row in meal_type_result:
            meal_types.append(row.meal_type)
    
    return meal_types


def get_cuisine_type(recipe_id: int):
    find_cuisine_stmt = sqlalchemy.select(
            db.cuisine_type.c.cuisine_type,
        ).select_from(db.cuisine_type.join(db.recipe_cuisine_types, db.cuisine_type.c.cuisine_type_id == db.recipe_cuisine_types.c.cuisine_type_id)).\
        where(db.recipe_cuisine_types.c.recipe_id == recipe_id)
    
    with db.engine.connect() as conn:
        cuisine_result = conn.execute(find_cuisine_stmt)
        if cuisine_result.rowcount == 0:
            raise HTTPException(status_code=404, detail="cuisine type not found")
        
        cuisines = []
        for row in cuisine_result:
            cuisines.append(row.cuisine_type)
    
    return cuisines

def get_ingredients(recipe_id: int):
    find_ingriedients_stmt = sqlalchemy.select(
            db.ingredient_quantities.c.ingredient_id,
            db.ingredient_quantities.c.amount,
            db.ingredient_quantities.c.unit_type,
            db.ingredients.c.ingredient_name,
    ).select_from(db.ingredient_quantities.join(db.ingredients, db.ingredients.c.ingredient_id == db.ingredient_quantities.c.ingredient_id)).\
        where(db.ingredient_quantities.c.recipe_id == recipe_id)
    
    with db.engine.connect() as conn:
        ingredients_result = conn.execute(find_ingriedients_stmt)
        if ingredients_result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no ingredients found matching recipe_id")
        
        ingriedients = []
        for row in ingredients_result:
            ingriedient_string = str(row.ingredient_name) + ": " + str(row.amount) + " " + str(row.unit_type)
            ingriedients.append(ingriedient_string)
        return ingriedients


class recipe_sort_options(str, Enum):
    recipe = "recipe"
    time = "time"
    number_of_favorites = "number_of_favorites"

@router.get("/recipes/", tags=["recipes"])
def list_recipe(recipe: str = "",
    cuisine: str = "",
    meal_type: str = "",
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
    sort: recipe_sort_options = recipe_sort_options.recipe):
    """
    This endpoint returns a list of recipes. For each recipe it returns:
    * `recipe_id`: the internal id of the character. Can be used to query the
      `/recipes/{recipe_id}` endpoint.
    * `recipe`: The name of the recipe.
    * `cuisine`: The cuisine that the recipe is from.
    * `meal_type`: The meal type that the recipe is from.
    * `time`: time needed to make the recipe.
    * `instructions`: instrustion to make the recipe.
    * `number_of_favorites`: number of users who have favorited recipe.


    You can filter for recipes whose name contains a string by using the
    `recipe` query parameter. You can filter for recipes by cuisine by using the
    `cuisine` query parameter. You can filter for recipes by meal-type by using the
    `type` query parameter. 

    You can also sort the results by using the `sort` query parameter:
    * `recipe` - Sort by recipe name alphabetically.
    * `time` - Sort by cooking time.
    * `number_of_favorites` - Sort by number of users who have favorited recipe.


    The `limit` and `offset` query parameters are used for pagination.
    The `limit` query parameter specifies the maximum number of results to return.
    The `offset` query parameter specifies the number of results to skip before
    returning results.
    """
    if sort == recipe_sort_options.recipe:
        sort_by = db.recipes.c.recipe_name
    elif sort == recipe_sort_options.time:
        sort_by = db.recipes.c.prep_time_mins
    elif sort == recipe_sort_options.number_of_favorites:
        sort_by = db.recipes.c.number_of_favorites.desc()

    stmt = (
        sqlalchemy.select(db.recipes.c.recipe_id,
                          db.recipes.c.recipe_name,
                          db.recipes.c.prep_time_mins,
                          db.recipes.c.recipe_instructions,
                          db.recipes.c.number_of_favorites).select_from(db.recipes
            .outerjoin(db.favorited_recipes, db.recipes.c.recipe_id == db.favorited_recipes.c.recipe_id)
        ).group_by(db.recipes.c.recipe_id).order_by(sort_by).limit(limit).offset(offset).distinct()

     )
    
    if recipe != "":
        stmt = stmt.where(db.recipes.c.recipe_name.ilike(f"%{recipe}%"))

    if cuisine != "":
        stmt = stmt.where(db.cuisine_type.c.cuisine_type.ilike(f"%{cuisine}%"))

    if meal_type != "":
        stmt = stmt.where(db.meal_type.c.meal_type.ilike(f"%{meal_type}%"))

    with db.engine.connect() as conn:
        result = conn.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no recipes found")
        json = {}
        json["recipes"] = []
        for row in result:
            json["recipes"].append({"recipe_id": row[0], "recipe_name": row[1], "cuisine": get_cuisine_type(row[0]),
                                     "meal_type": get_meal_type(row[0]), "prep_time_mins": str(row[2]) + " minutes",
                                       "instructions": row[3], "number_of_favorites": row[4]})
        return json
    




class IngredientsJson(BaseModel):
    ingredient_id: int
    unit_type: Optional[str]
    amount: Optional[int]
    ingredient_price_usd: Optional[float]


class recipeJson(BaseModel):
    recipe: str
    cuisine_id: Optional[List[int]]
    meal_type_id: Optional[List[int]]
    calories: Optional[int]
    time: Optional[int]
    recipe_instructions: Optional[str]
    url: Optional[str]
    ingredients: Optional[List[IngredientsJson]]


# all parameters are optional except the recipe name
# all parameters are passed in from the request body now
# complex transaction function since it uses commit(), rollback(), implements data validation, performs multiple database operations
@router.post("/recipes/", tags=["recipes"])
def add_recipe(recipe: recipeJson):
    """
    This endpoint will allow users to add their own recipes to the API.
    To add a recipe, the user must provide:
    * `recipe`: The name of the recipe.
    * `cuisine_id`: The cuisine id(s) for the recipe cuisine(s).
    * `meal_type_id`: The meal type id(s) for the recipe meal type(s).
    * `calories`: Total calories in one serving of the recipe.
    * `time`: The total time it takes to make the recipe.
    * `recipe_instructions`: The instructions to make the recipe.
    * `url`: The url to the recipe.
    * `ingredients`: The list that contains the ingredients and amounts
      that are needed to make the recipe.
    """
    check_valid_recipe_stmt = sqlalchemy.select(db.recipes.c.recipe_id).where(db.recipes.c.recipe_name == recipe.recipe)
    with db.engine.begin() as conn:
        result = conn.execute(check_valid_recipe_stmt)
        if result.rowcount != 0:
            raise HTTPException(status_code=409, detail="recipe already exists")
        stmt = sqlalchemy.insert(db.recipes).values(recipe_name=recipe.recipe, calories=recipe.calories,
                                                    prep_time_mins=recipe.time, recipe_instructions=recipe.recipe_instructions,
                                                    recipe_url=recipe.url, number_of_favorites=0)
        result = conn.execute(stmt)
        recipe_id = result.inserted_primary_key[0]
        if recipe.cuisine_id is not None:
            for cuisine in recipe.cuisine_id:
                check_valid_cuisine_stmt = sqlalchemy.select(db.cuisine_type.c.cuisine_type).where(db.cuisine_type.c.cuisine_type_id == cuisine)
                check_valid_result = conn.execute(check_valid_cuisine_stmt)
                if check_valid_result.rowcount == 0:
                    conn.rollback()
                    raise HTTPException(status_code=400, detail="invalid cuisine id")
                stmt = sqlalchemy.insert(db.recipe_cuisine_types).values(recipe_id=recipe_id, cuisine_id=cuisine)
                conn.execute(stmt)
        if recipe.meal_type_id is not None:
            for meal_type in recipe.meal_type_id:
                check_valid_meal_type_stmt = sqlalchemy.select(db.meal_type.c.meal_type).where(db.meal_type.c.meal_type_id == meal_type)
                check_valid_result = conn.execute(check_valid_meal_type_stmt)
                if check_valid_result.rowcount == 0:
                    conn.rollback()
                    raise HTTPException(status_code=400, detail="invalid meal type id")
                stmt = sqlalchemy.insert(db.recipe_meal_types).values(recipe_id=recipe_id, meal_type_id=meal_type)
                conn.execute(stmt)
        if recipe.ingredients is not None:
            for ingredient in recipe.ingredients:
                check_valid_ingredient_stmt = sqlalchemy.select(db.ingredients.c.ingredient_name).where(db.ingredients.c.ingredient_id == ingredient.ingredient_id)
                check_valid_result = conn.execute(check_valid_ingredient_stmt)
                if check_valid_result.rowcount == 0:
                    conn.rollback()
                    raise HTTPException(status_code=400, detail="invalid ingredient id")
                stmt = sqlalchemy.insert(db.ingredient_quantities).values(recipe_id=recipe_id, ingredient_id= ingredient.ingredient_id,
                                                                            unit_type=ingredient.unit_type, amount=ingredient.amount, ingredient_cost=ingredient.ingredient_price_usd)
                conn.execute(stmt)
            
        return {"recipe_id": recipe_id}

# replaced post call with put call
# parameters include ids instead of names so the function wouldn't have to look up the names and match them
# made fields such as new_ingredient_cost, new_amount, and new_unit_type optional
@router.put("/recipes/{recipe_id}/", tags=["recipes"])
def modify_recipe(
    recipe_id: int,
    old_ingredient_id: int,
    new_ingredient_name: str,
    new_unit_type: Optional[str] = None,
    new_amount: Optional[str] = None,
    new_ingredient_cost: Optional[float] = None,
):
    with db.engine.connect() as conn:
        if old_ingredient_id and new_ingredient_name:
            ingredient_update_query = update(db.ingredients).where(
                db.ingredients.c.ingredient_id == old_ingredient_id
            ).values(
                ingredient_name=new_ingredient_name
            )
            conn.execute(ingredient_update_query)
            ingredient_quantity_update_query = update(db.ingredient_quantities).where(
                (db.ingredient_quantities.c.recipe_id == recipe_id)
                & (db.ingredient_quantities.c.ingredient_id == old_ingredient_id)
            )
            if new_unit_type is not None:
                ingredient_quantity_update_query = ingredient_quantity_update_query.values(
                    unit_type=new_unit_type
                )
            if new_amount is not None:
                ingredient_quantity_update_query = ingredient_quantity_update_query.values(
                    amount=new_amount
                )
            if new_ingredient_cost is not None:
                ingredient_quantity_update_query = ingredient_quantity_update_query.values(
                    ingredient_price_usd=new_ingredient_cost
                )
            
            if new_unit_type is not None or new_amount is not None or new_ingredient_cost is not None:
                conn.execute(ingredient_quantity_update_query)
                conn.commit()
            
            return f"Ingredient with ID {old_ingredient_id} updated to '{new_ingredient_name}' and ingredient information updated in recipe with ID {recipe_id}"
        else:
            return "Please provide both old ingredient ID and new ingredient name"


def get_user_id(username: str):
    stmt = sqlalchemy.select(db.users.c.user_id).where(db.users.c.user_name == username)

    user_id = -1

    with db.engine.connect() as conn:
        result = conn.execute(stmt)
        for row in result:
            user_id = row.user_id

    if user_id == -1:
        raise HTTPException(status_code=404, detail="user not found")
    return user_id


#add username to parameters
@router.put("/favorited_recipes/", tags=["favorited_recipes"])
def favorite_recipe(username: str, recipe_id: int
    ):
    """
    This endpoint will allow users to add existing recipes to their favorites list. 
    The user must provide their username to favorite a recipe.
    """
    user_id = get_user_id(username)

    find_recipe_stmt = sqlalchemy.select(db.recipes.c.recipe_id).where(db.recipes.c.recipe_id == recipe_id)

    with db.engine.connect() as conn:
        transaction = conn.begin()
        find_recipe_result = conn.execute(find_recipe_stmt)

        if find_recipe_result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe not found.")
        try:
            conn.execute(
                    sqlalchemy.insert(db.favorited_recipes),
                    [
                        {"recipe_id": recipe_id,
                        "user_id": user_id,
                        "date_favorited": str(datetime.datetime.now())}
                    ]
                )
                #exception will occur here if the recipe is already in the favorites list
            transaction.commit()
            #updates the number of favorites for the recipe if it is not already in the favorited by the user
            update_num_favs_stmt = sqlalchemy.update(db.recipes).where(db.recipes.c.recipe_id == recipe_id).values(number_of_favorites = db.recipes.c.number_of_favorites + 1)
            conn.execute(update_num_favs_stmt)
            conn.commit()
        #if the recipe is already in the favorites list, updates the date_favorited
        except sqlalchemy.exc.IntegrityError: 
            transaction.rollback()
            update_favorite_stmt = sqlalchemy.update(db.favorited_recipes).where(db.favorited_recipes.c.recipe_id == recipe_id and db.favorited_recipes.c.user_id == user_id).values(date_favorited = str(datetime.datetime.now()))
            conn.execute(update_favorite_stmt)

    return {"recipe_id": recipe_id,
            "user_id": user_id} 

@router.delete("/favorited_recipes/", tags=["favorited_recipes"])
def unfavorite_recipe(username: str, recipe_id: int
    ):
    """
    This endpoint will allow users to remove existing recipes from their favorites list. 
   
    """
    user_id = get_user_id(username)

    find_recipe_stmt = sqlalchemy.select(db.recipes.c.recipe_id).where(db.recipes.c.recipe_id == recipe_id)

    delete_favorite_stmt = sqlalchemy.delete(db.favorited_recipes).where(db.favorited_recipes.c.recipe_id == recipe_id and db.favorited_recipes.c.user_id == user_id)

    decrement_num_favs_stmt = sqlalchemy.update(db.recipes).where(db.recipes.c.recipe_id == recipe_id).values(number_of_favorites = db.recipes.c.number_of_favorites - 1)

    with db.engine.connect() as conn:
        transaction = conn.begin()
        find_recipe_result = conn.execute(find_recipe_stmt)

        if find_recipe_result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe does not exist.")
        try:
            conn.execute(delete_favorite_stmt)
            transaction.commit()
            conn.execute(decrement_num_favs_stmt)
            conn.commit()
        except sqlalchemy.exc.IntegrityError:
            transaction.rollback()
    
    return {"recipe_id": recipe_id,
            "user_id": user_id} 


@router.get("/favorited_recipes/", tags=["favorited_recipes"])
def list_favorite_recipes(username: str, 
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
    sort: recipe_sort_options = recipe_sort_options.recipe
    ):
    """
    This endpoint will list all recipes in the users favorites list. For each recipe it returns:
    * `recipe_id`: the internal id of the character. Can be used to query the
      `/recipes/{recipe_id}` endpoint.
    * `recipe`: The name of the recipe.
    * `cuisine`: The cuisine that the recipe is from.
    * `meal_type`: The meal type that the recipe is from.
    * `ingredients`: The listed ingredients and amounts that are needed to make the recipe.
    * `prep_time_mins`: time needed to make the recipe.

    You can also sort the results by using the `sort` query parameter:
    * `recipe` - Sort by recipe name alphabetically.
    * `time` - Sort by cooking time.

    The `limit` and `offset` query parameters are used for pagination.
    The `limit` query parameter specifies the maximum number of results to return.
    The `offset` query parameter specifies the number of results to skip before
    """
    if sort == recipe_sort_options.time:
        sort_by = db.recipes.c.prep_time_mins
    else:
        sort_by = db.recipes.c.recipe_name
    
    user_id = get_user_id(username)

    stmt = sqlalchemy.select(db.recipes.c.recipe_id, db.recipes.c.recipe_name, db.recipes.c.prep_time_mins).\
            where(db.recipes.c.recipe_id == db.favorited_recipes.c.recipe_id and db.favorited_recipes.c.user_id == user_id).\
            order_by(sort_by).\
            limit(limit).\
            offset(offset)

    favorited_recipes = []
    with db.engine.connect() as conn:
        favorited_results = conn.execute(stmt)
        for row in favorited_results:
            favorited_recipes.append({
                "recipe_id": row.recipe_id,
                "recipe": row.recipe_name,
                "cuisine": get_cuisine_type(row.recipe_id),
                "meal_type": get_meal_type(row.recipe_id),
                "ingredients": get_ingredients(row.recipe_id),
                "prep_time_mins": row.prep_time_mins
            })

    return favorited_recipes
