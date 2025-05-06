import os
import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import parse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(filename='flask.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/rutur/mynetdiary_project/tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    sex = db.Column(db.String(10))
    dob = db.Column(db.String(10))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    target_weight = db.Column(db.Float)
    activity_level = db.Column(db.String(20))
    dietary_pref = db.Column(db.String(20))
    health_goal = db.Column(db.String(20))

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    vegetarian = db.Column(db.Boolean, nullable=False)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    calories_per_hour = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), nullable=False)

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'), nullable=False)
    servings = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    food = db.relationship('Food', backref='logs')

class ExerciseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    exercise = db.relationship('Exercise', backref='logs')

class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.String(10), nullable=False)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class OnboardingForm(FlaskForm):
    sex = SelectField('Sex', choices=[('male', 'Male'), ('female', 'Female')], validators=[DataRequired()])
    dob = StringField('Date of Birth (YYYY-MM-DD)', validators=[DataRequired()])
    height = FloatField('Height (cm)', validators=[DataRequired(), NumberRange(min=100, max=250)])
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=30, max=200)])
    target_weight = FloatField('Target Weight (kg)', validators=[DataRequired(), NumberRange(min=30, max=200)])
    activity_level = SelectField('Activity Level', choices=[('sedentary', 'Sedentary'), ('light', 'Light'), ('moderate', 'Moderate'), ('active', 'Active'), ('very active', 'Very Active')], validators=[DataRequired()])
    dietary_pref = SelectField('Dietary Preference', choices=[('vegetarian', 'Vegetarian'), ('non-vegetarian', 'Non-Vegetarian')], validators=[DataRequired()])
    health_goal = SelectField('Health Goal', choices=[('loss', 'Weight Loss'), ('maintain', 'Maintain'), ('gain', 'Weight Gain')], validators=[DataRequired()])
    submit = SubmitField('Save Profile')

class FoodLogForm(FlaskForm):
    food = SelectField('Food', coerce=int, validators=[DataRequired()])
    servings = FloatField('Servings', validators=[DataRequired(), NumberRange(min=0.1)])
    submit = SubmitField('Log Food')

class ExerciseLogForm(FlaskForm):
    exercise = SelectField('Exercise', coerce=int, validators=[DataRequired()])
    hours = FloatField('Hours', validators=[DataRequired(), NumberRange(min=0.1)])
    submit = SubmitField('Log Exercise')

class WeightLogForm(FlaskForm):
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=30, max=200)])
    submit = SubmitField('Log Weight')

class ProgressForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    period = SelectField('Period', choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month')], validators=[DataRequired()])
    submit = SubmitField('View Progress')

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Initialization
def init_db():
    try:
        db_path = 'C:\\Users\\rutur\\mynetdiary_project\\tracker.db'
        logger.debug(f"Checking database at {db_path}")
        print(f"Checking database at {db_path}")

        if not os.path.exists(db_path):
            open(db_path, 'a').close()
            logger.debug("Database file created")
            print("Database file created")

        try:
            os.chmod(db_path, 0o666)
            logger.debug("Set permissions on tracker.db")
            print("Set permissions on tracker.db")
        except Exception as e:
            logger.warning(f"Failed to set permissions on {db_path}: {e}")
            print(f"Failed to set permissions on {db_path}: {e}")

        with app.app_context():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(user)")
            columns = [info[1] for info in cursor.fetchall()]
            expected_columns = [
                'id', 'username', 'password', 'sex', 'dob', 'height', 'weight',
                'target_weight', 'activity_level', 'dietary_pref', 'health_goal'
            ]

            if set(columns) != set(expected_columns):
                logger.debug("User table schema mismatch detected. Recreating user table.")
                print("User table schema mismatch detected. Recreating user table.")
                try:
                    cursor.execute('DROP TABLE IF EXISTS user')
                    cursor.execute('''
                        CREATE TABLE user (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL,
                            sex TEXT,
                            dob TEXT,
                            height REAL,
                            weight REAL,
                            target_weight REAL,
                            activity_level TEXT,
                            dietary_pref TEXT,
                            health_goal TEXT
                        )
                    ''')
                    conn.commit()
                    logger.debug("User table recreated with correct schema")
                    print("User table recreated with correct schema")
                except Exception as e:
                    logger.error(f"Failed to recreate user table: {e}")
                    print(f"Failed to recreate user table: {e}")
                    conn.close()
                    raise
            conn.close()

            logger.debug("Creating tables...")
            print("Creating tables...")
            try:
                db.create_all()
                db.session.commit()
                logger.debug("Tables created")
                print("Tables created")
            except Exception as e:
                logger.error(f"Failed to create tables: {e}")
                print(f"Failed to create tables: {e}")
                raise

            logger.debug("Clearing Food and Exercise tables...")
            print("Clearing Food and Exercise tables...")
            try:
                db.session.query(Food).delete()
                db.session.query(Exercise).delete()
                db.session.commit()
                logger.debug("Cleared Food and Exercise tables")
                print("Cleared Food and Exercise tables")
            except Exception as e:
                logger.error(f"Failed to clear Food and Exercise tables: {e}")
                print(f"Failed to clear Food and Exercise tables: {e}")
                db.session.rollback()
                raise

            foods = [
                Food(name="Paneer Tikka", calories=280, protein=14, carbs=10, fat=20, vegetarian=True),
                Food(name="Vegetable Biryani", calories=320, protein=8, carbs=50, fat=10, vegetarian=True),
                Food(name="Tofu Stir-Fry", calories=200, protein=12, carbs=15, fat=10, vegetarian=True),
                Food(name="Chana Masala", calories=240, protein=10, carbs=35, fat=6, vegetarian=True),
                Food(name="Palak Paneer", calories=300, protein=15, carbs=12, fat=22, vegetarian=True),
                Food(name="Mushroom Curry", calories=220, protein=6, carbs=20, fat=12, vegetarian=True),
                Food(name="Veggie Wrap", calories=250, protein=8, carbs=40, fat=8, vegetarian=True),
                Food(name="Lentil Dal", calories=190, protein=12, carbs=30, fat=2, vegetarian=True),
                Food(name="Avocado Toast", calories=200, protein=5, carbs=25, fat=10, vegetarian=True),
                Food(name="Falafel Pita", calories=270, protein=9, carbs=35, fat=12, vegetarian=True),
                Food(name="Spinach Smoothie", calories=150, protein=5, carbs=20, fat=5, vegetarian=True),
                Food(name="Grilled Chicken Breast", calories=300, protein=30, carbs=0, fat=10, vegetarian=False),
                Food(name="Salmon Fillet", calories=400, protein=35, carbs=0, fat=20, vegetarian=False),
                Food(name="Beef Stir-Fry", calories=350, protein=32, carbs=10, fat=18, vegetarian=False),
                Food(name="Tuna Salad", calories=280, protein=25, carbs=10, fat=15, vegetarian=False),
                Food(name="Lamb Curry", calories=380, protein=28, carbs=15, fat=25, vegetarian=False),
                Food(name="Shrimp Fried Rice", calories=320, protein=20, carbs=40, fat=10, vegetarian=False),
                Food(name="Turkey Burger", calories=300, protein=25, carbs=20, fat=15, vegetarian=False),
                Food(name="Chicken Caesar Salad", calories=260, protein=22, carbs=15, fat=12, vegetarian=False),
                Food(name="Pork Tenderloin", calories=340, protein=30, carbs=0, fat=22, vegetarian=False),
                Food(name="Egg Omelette with Ham", calories=240, protein=18, carbs=5, fat=16, vegetarian=False)
            ]
            logger.debug(f"Inserting {len(foods)} foods...")
            print(f"Inserting {len(foods)} foods...")
            try:
                for food in foods:
                    db.session.add(food)
                db.session.commit()
                food_count = db.session.query(Food).count()
                logger.debug(f"Food table initialized with {food_count} entries")
                print(f"Food table initialized with {food_count} entries")
                if food_count != 21:
                    logger.error(f"Expected 21 foods, got {food_count}")
                    print(f"Expected 21 foods, got {food_count}")
            except Exception as e:
                logger.error(f"Failed to insert foods: {e}")
                print(f"Failed to insert foods: {e}")
                db.session.rollback()
                raise

            exercises = [
                Exercise(name="Running", calories_per_hour=600, type="cardio"),
                Exercise(name="Weight Lifting", calories_per_hour=400, type="strength"),
                Exercise(name="Yoga", calories_per_hour=200, type="mixed"),
                Exercise(name="Cycling", calories_per_hour=500, type="cardio"),
                Exercise(name="Swimming", calories_per_hour=550, type="cardio"),
                Exercise(name="HIIT Workout", calories_per_hour=450, type="cardio"),
                Exercise(name="Pilates", calories_per_hour=250, type="mixed"),
                Exercise(name="Jump Rope", calories_per_hour=600, type="cardio"),
                Exercise(name="Walking", calories_per_hour=300, type="cardio"),
                Exercise(name="Bodyweight Circuit", calories_per_hour=350, type="strength")
            ]
            logger.debug(f"Inserting {len(exercises)} exercises...")
            print(f"Inserting {len(exercises)} exercises...")
            try:
                for exercise in exercises:
                    db.session.add(exercise)
                db.session.commit()
                exercise_count = db.session.query(Exercise).count()
                logger.debug(f"Exercise table initialized with {exercise_count} entries")
                print(f"Exercise table initialized with {exercise_count} entries")
                if exercise_count != 10:
                    logger.error(f"Expected 10 exercises, got {exercise_count}")
                    print(f"Expected 10 exercises, got {exercise_count}")
            except Exception as e:
                logger.error(f"Failed to insert exercises: {e}")
                print(f"Failed to insert exercises: {e}")
                db.session.rollback()
                raise

            db.session.commit()
            logger.debug("Database initialization completed with final commit")
            print("Database initialization completed with final commit")
    except Exception as e:
        logger.error(f"Database init error: {e}")
        print(f"Database init error: {e}")
        raise

# Utility Functions
def default_dashboard_args():
    food_form = FoodLogForm()
    exercise_form = ExerciseLogForm()
    food_form.food.choices = [(-1, "No foods available")]
    exercise_form.exercise.choices = [(-1, "No exercises available")]
    return {
        'food_form': food_form,
        'exercise_form': exercise_form,
        'weight_form': WeightLogForm(),
        'progress_form': ProgressForm(),
        'profile_complete': False,
        'meals': [],
        'exercises': [],
        'liked_food_ids': [],
        'liked_exercise_ids': [],
        'selected_date': datetime.now().date(),
        'selected_period': 'day',
        'total_calories_consumed': 0,
        'stats': {'exercise': 0},
        'macros': {
            'carbs': {'consumed': 0, 'target': 182, 'percentage': 0, 'remaining': 182},
            'protein': {'consumed': 0, 'target': 81, 'percentage': 0, 'remaining': 81},
            'fat': {'consumed': 0, 'target': 63, 'percentage': 0, 'remaining': 63}
        },
        'has_non_zero_net_calories': False,
        'net_calories_dates': [],
        'net_calories_values': [],
        'fitness_score': 0,
        'fitness_recommendations': []
    }

def check_db_content():
    try:
        food_count = Food.query.count()
        exercise_count = Exercise.query.count()
        return food_count, exercise_count
    except Exception as e:
        logger.error(f"Error checking database content: {e}")
        return 0, 0

def calculate_calories(user):
    try:
        age = (datetime.now().date() - parse(user.dob).date()).days // 365
        if user.sex == 'male':
            bmr = 10 * user.weight + 6.25 * user.height - 5 * age + 5
        else:
            bmr = 10 * user.weight + 6.25 * user.height - 5 * age - 161
        activity_multipliers = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725, 'very active': 1.9}
        tdee = bmr * activity_multipliers.get(user.activity_level, 1.55)
        goal_adjustments = {'loss': -500, 'maintain': 0, 'gain': 500}
        food_target = tdee + goal_adjustments.get(user.health_goal, -500)
        net_goal = goal_adjustments.get(user.health_goal, -500)
        return round(tdee), round(food_target), net_goal
    except Exception as e:
        logger.error(f"Error calculating calories: {e}")
        return 2000, 1500, -500

def calculate_fitness_score(user):
    try:
        if not all([user.dob, user.weight, user.height, user.activity_level, user.health_goal, user.sex]):
            return 0, ["Complete your profile to get a fitness assessment."]
        
        # Calculate BMI
        height_m = user.height / 100
        bmi = user.weight / (height_m ** 2)
        bmi_score = 0
        if 18.5 <= bmi <= 24.9:
            bmi_score = 40  # Healthy BMI contributes significantly
        elif 25 <= bmi <= 29.9 or 16.5 <= bmi < 18.5:
            bmi_score = 20  # Overweight or underweight
        else:
            bmi_score = 10  # Obese or severely underweight

        # Activity level score
        activity_scores = {
            'sedentary': 10,
            'light': 20,
            'moderate': 30,
            'active': 40,
            'very active': 50
        }
        activity_score = activity_scores.get(user.activity_level, 10)

        # Weight progress score
        weight_logs = WeightLog.query.filter_by(user_id=user.id).order_by(WeightLog.date.asc()).all()
        weight_progress_score = 0
        if weight_logs and len(weight_logs) > 1:
            initial_weight = weight_logs[0].weight
            current_weight = weight_logs[-1].weight
            target_weight = user.target_weight
            if user.health_goal == 'loss' and current_weight < initial_weight:
                progress = (initial_weight - current_weight) / (initial_weight - target_weight) * 100
                weight_progress_score = min(30, max(10, progress / 2))
            elif user.health_goal == 'gain' and current_weight > initial_weight:
                progress = (current_weight - initial_weight) / (target_weight - initial_weight) * 100
                weight_progress_score = min(30, max(10, progress / 2))
            elif user.health_goal == 'maintain' and abs(current_weight - target_weight) < 2:
                weight_progress_score = 30

        # Total fitness score
        fitness_score = min(100, round(bmi_score + activity_score + weight_progress_score))

        # Fitness recommendations
        recommendations = []
        if bmi < 18.5:
            recommendations.append("Increase caloric intake with nutrient-dense foods to reach a healthy weight.")
        elif bmi > 24.9:
            recommendations.append("Incorporate regular cardio and strength training to reduce body fat.")
        if activity_score < 30:
            recommendations.append("Aim for at least 150 minutes of moderate aerobic activity or 75 minutes of vigorous activity per week.")
        if weight_progress_score < 20:
            recommendations.append("Track your food and exercise consistently to make steady progress toward your goal.")
        if not recommendations:
            recommendations.append("You're on track! Maintain your current activity and nutrition plan.")

        return fitness_score, recommendations
    except Exception as e:
        logger.error(f"Error calculating fitness score: {e}")
        return 0, ["Error calculating fitness score. Please try again later."]

def recommend_meals(user, food_target):
    try:
        meals = []
        if user.dietary_pref == 'vegetarian':
            meals = Food.query.filter_by(vegetarian=True).all()
        else:
            meals = Food.query.all()
        meal_calories = sum(meal.calories for meal in meals[:5])
        return meals[:5], meal_calories
    except Exception as e:
        logger.error(f"Error recommending meals: {e}")
        return [], 0

def recommend_exercises(user):
    try:
        exercises = Exercise.query.all()
        exercise_calories = sum(ex.calories_per_hour for ex in exercises[:5])
        return exercises[:5], exercise_calories
    except Exception as e:
        logger.error(f"Error recommending exercises: {e}")
        return [], 0

def generate_weight_plan(user):
    try:
        if not all([user.dob, user.weight, user.height, user.activity_level, user.health_goal, user.sex]):
            return {
                'calorie_target': 1500,
                'exercise_plan': "Complete your profile for a personalized exercise plan.",
                'meal_plan': "Complete your profile for a personalized meal plan.",
                'timeline': "N/A"
            }

        tdee, food_target, net_goal = calculate_calories(user)
        weight_diff = abs(user.weight - user.target_weight)
        weeks_needed = 0
        if user.health_goal == 'loss':
            weeks_needed = round(weight_diff / 0.5)  # 0.5 kg/week is a safe rate
        elif user.health_goal == 'gain':
            weeks_needed = round(weight_diff / 0.25)  # 0.25 kg/week for muscle gain
        else:
            weeks_needed = 0

        exercise_plan = []
        if user.activity_level in ['sedentary', 'light']:
            exercise_plan.append("30 minutes of moderate cardio (e.g., brisk walking, cycling) 5 days/week.")
            exercise_plan.append("2-3 strength training sessions/week focusing on major muscle groups.")
        elif user.activity_level == 'moderate':
            exercise_plan.append("45 minutes of vigorous cardio (e.g., running, swimming) 4-5 days/week.")
            exercise_plan.append("3 strength training sessions/week with progressive overload.")
        else:
            exercise_plan.append("60 minutes of mixed cardio and strength training 5-6 days/week.")
            exercise_plan.append("Incorporate flexibility and recovery sessions (e.g., yoga, stretching).")

        meal_plan = []
        if user.dietary_pref == 'vegetarian':
            meal_plan.append(f"Daily caloric intake: {food_target} kcal with 50% carbs, 25% protein, 25% fat.")
            meal_plan.append("Sample meals: Lentil Dal, Tofu Stir-Fry, Avocado Toast.")
        else:
            meal_plan.append(f"Daily caloric intake: {food_target} kcal with 50% carbs, 25% protein, 25% fat.")
            meal_plan.append("Sample meals: Grilled Chicken Breast, Salmon Fillet, Vegetable Biryani.")

        timeline = f"Reach your target weight in approximately {weeks_needed} weeks with consistent adherence."
        if user.health_goal == 'maintain':
            timeline = "Maintain your current weight with balanced nutrition and regular exercise."

        return {
            'calorie_target': food_target,
            'exercise_plan': exercise_plan,
            'meal_plan': meal_plan,
            'timeline': timeline
        }
    except Exception as e:
        logger.error(f"Error generating weight plan: {e}")
        return {
            'calorie_target': 1500,
            'exercise_plan': "Error generating plan. Please try again.",
            'meal_plan': "Error generating plan. Please try again.",
            'timeline': "N/A"
        }

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user)
                logger.debug(f"User {user.username} logged in")
                return redirect(url_for('dashboard'))
            flash('Invalid username or password.', 'error')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Failed to log in due to a database issue. Please try again or contact support.', 'error')
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = SignupForm()
    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            logger.debug(f"User {form.username.data} signed up")
            login_user(new_user)
            flash('Account created successfully! Please complete your profile.', 'success')
            return redirect(url_for('onboarding'))
        except Exception as e:
            logger.error(f"Signup error: {e}")
            db.session.rollback()
            flash('Username already exists or database issue.', 'error')
    return render_template('signup.html', form=form)

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    form = OnboardingForm()
    if form.validate_on_submit():
        try:
            current_user.sex = form.sex.data
            current_user.dob = form.dob.data
            current_user.height = form.height.data
            current_user.weight = form.weight.data
            current_user.target_weight = form.target_weight.data
            current_user.activity_level = form.activity_level.data
            current_user.dietary_pref = form.dietary_pref.data
            current_user.health_goal = form.health_goal.data
            db.session.commit()
            logger.debug(f"User {current_user.username} completed onboarding")
            flash('Profile saved successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            db.session.rollback()
            flash('Failed to save profile.', 'error')
    return render_template('onboarding.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    try:
        food_form = FoodLogForm()
        exercise_form = ExerciseLogForm()
        weight_form = WeightLogForm()
        progress_form = ProgressForm()
        logger.debug("Initialized forms for dashboard")

        try:
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            Session = sessionmaker(bind=engine)
            form_session = Session()
            try:
                foods = form_session.query(Food).order_by(Food.name).all()
                exercises = form_session.query(Exercise).order_by(Exercise.name).all()
                logger.debug(f"Form session - Raw food count: {len(foods)}, Raw exercise count: {len(exercises)}")
                food_options = [(f.id, f.name) for f in foods]
                exercise_options = [(e.id, e.name) for e in exercises]
                if not food_options:
                    logger.warning("No food options found in form session, setting default")
                    food_options = [(-1, "No foods available")]
                if not exercise_options:
                    logger.warning("No exercise options found in form session, setting default")
                    exercise_options = [(-1, "No exercises available")]
                logger.debug(f"Form session - Loaded {len(food_options)} food options, {len(exercise_options)} exercise options")
                food_form.food.choices = food_options
                exercise_form.exercise.choices = exercise_options
            except Exception as e:
                logger.error(f"Failed to load food/exercise options in form session: {e}")
                flash('Failed to load food/exercise options.', 'error')
                food_form.food.choices = [(-1, "No foods available")]
                exercise_form.exercise.choices = [(-1, "No exercises available")]
            finally:
                form_session.close()
        except Exception as e:
            logger.error(f"Failed to create form session: {e}")
            flash('Failed to initialize form options.', 'error')
            food_form.food.choices = [(-1, "No foods available")]
            exercise_form.exercise.choices = [(-1, "No exercises available")]

        try:
            liked_foods = db.session.query(Feedback).filter_by(user_id=current_user.id, item_type='food', rating='like').all()
            liked_exercises = db.session.query(Feedback).filter_by(user_id=current_user.id, item_type='exercise', rating='like').all()
            liked_food_ids = [f.item_id for f in liked_foods]
            liked_exercise_ids = [e.item_id for e in liked_exercises]
            logger.debug(f"Loaded liked items: {len(liked_food_ids)} foods, {len(liked_exercise_ids)} exercises")
        except Exception as e:
            logger.error(f"Failed to load liked items: {e}")
            liked_food_ids = []
            liked_exercise_ids = []

        try:
            food_count, exercise_count = check_db_content()
            logger.debug(f"Database check: Foods={food_count}, Exercises={exercise_count}")
            if food_count == 0 or exercise_count == 0:
                flash('No food or exercise data available. Please contact support.', 'error')
        except Exception as e:
            logger.error(f"Error checking database content: {e}")
            flash('Failed to load dashboard due to database issue.', 'error')

        profile_complete = all([
            current_user.dob,
            current_user.weight is not None and current_user.weight > 0,
            current_user.height is not None and current_user.height > 0,
            current_user.activity_level,
            current_user.health_goal,
            current_user.sex
        ])
        logger.debug(f"Profile complete: {profile_complete}")

        fitness_score, fitness_recommendations = calculate_fitness_score(current_user)

        if profile_complete:
            tdee, food_target, net_goal = calculate_calories(current_user)
            meals, meal_calories = recommend_meals(current_user, food_target)
            exercises, exercise_calories = recommend_exercises(current_user)
        else:
            tdee, food_target, net_goal = 2000, 1500, -500
            meals, meal_calories = [], 0
            exercises, exercise_calories = [], 0
        logger.debug(f"Calculated: TDEE={tdee}, Food Target={food_target}, Meals={len(meals)}, Exercises={len(exercises)}")

        selected_date = datetime.now().date()
        selected_period = 'day'

        if progress_form.validate_on_submit() and progress_form.submit.data:
            selected_date = progress_form.date.data
            selected_period = progress_form.period.data
            logger.debug(f"Progress form submitted: date={selected_date}, period={selected_period}")

        if food_form.validate_on_submit() and food_form.submit.data:
            try:
                food_id = int(food_form.food.data)
                servings = float(food_form.servings.data)
                if food_id > 0 and servings > 0:
                    food_log = FoodLog(user_id=current_user.id, food_id=food_id, servings=servings, date=datetime.now().date())
                    db.session.add(food_log)
                    db.session.commit()
                    flash('Food logged successfully!', 'success')
                else:
                    flash('Invalid food or servings.', 'error')
            except Exception as e:
                logger.error(f"Error logging food: {e}")
                flash('Failed to log food.', 'error')
            return redirect(url_for('dashboard'))

        if exercise_form.validate_on_submit() and exercise_form.submit.data:
            try:
                exercise_id = int(exercise_form.exercise.data)
                hours = float(exercise_form.hours.data)
                if exercise_id > 0 and hours > 0:
                    exercise_log = ExerciseLog(user_id=current_user.id, exercise_id=exercise_id, hours=hours, date=datetime.now().date())
                    db.session.add(exercise_log)
                    db.session.commit()
                    flash('Exercise logged successfully!', 'success')
                else:
                    flash('Invalid exercise or hours.', 'error')
            except Exception as e:
                logger.error(f"Error logging exercise: {e}")
                flash('Failed to log exercise.', 'error')
            return redirect(url_for('dashboard'))

        if weight_form.validate_on_submit() and weight_form.submit.data:
            try:
                weight = float(weight_form.weight.data)
                if weight > 0:
                    weight_log = WeightLog(user_id=current_user.id, weight=weight, date=datetime.now().date())
                    current_user.weight = weight
                    db.session.add(weight_log)
                    db.session.commit()
                    flash('Weight logged successfully!', 'success')
                else:
                    flash('Invalid weight.', 'error')
            except Exception as e:
                logger.error(f"Error logging weight: {e}")
                flash('Failed to log weight.', 'error')
            return redirect(url_for('dashboard'))

        try:
            start_date = selected_date
            if selected_period == 'week':
                start_date -= timedelta(days=6)
            elif selected_period == 'month':
                start_date -= timedelta(days=29)

            food_logs = FoodLog.query.filter(
                FoodLog.user_id == current_user.id,
                FoodLog.date >= start_date,
                FoodLog.date <= selected_date
            ).all()
            exercise_logs = ExerciseLog.query.filter(
                ExerciseLog.user_id == current_user.id,
                ExerciseLog.date >= start_date,
                ExerciseLog.date <= selected_date
            ).all()

            total_calories_consumed = sum(log.food.calories * log.servings for log in food_logs)
            stats = {'exercise': sum(log.exercise.calories_per_hour * log.hours for log in exercise_logs)}
            macros = {
                'carbs': {'consumed': sum(log.food.carbs * log.servings for log in food_logs), 'target': 182, 'percentage': 0, 'remaining': 182},
                'protein': {'consumed': sum(log.food.protein * log.servings for log in food_logs), 'target': 81, 'percentage': 0, 'remaining': 81},
                'fat': {'consumed': sum(log.food.fat * log.servings for log in food_logs), 'target': 63, 'percentage': 0, 'remaining': 63}
            }

            for m in macros:
                if macros[m]['target'] > 0:
                    macros[m]['percentage'] = int((macros[m]['consumed'] / macros[m]['target']) * 100)
                else:
                    macros[m]['percentage'] = 0
                macros[m]['remaining'] = max(0, macros[m]['target'] - macros[m]['consumed'])

            net_calories = []
            net_calories_dates = []
            current_date = start_date
            while current_date <= selected_date:
                daily_food = sum(log.food.calories * log.servings for log in food_logs if log.date == current_date)
                daily_exercise = sum(log.exercise.calories_per_hour * log.hours for log in exercise_logs if log.date == current_date)
                net_calories.append(daily_food - daily_exercise)
                net_calories_dates.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

            has_non_zero_net_calories = any(c != 0 for c in net_calories)
            logger.debug(f"Progress calculated: Calories consumed={total_calories_consumed}, Burned={stats['exercise']}, Net calories={net_calories}")
        except Exception as e:
            logger.error(f"Error calculating progress: {e}")
            flash('Failed to load progress data.', 'error')
            total_calories_consumed = 0
            stats = {'exercise': 0}
            macros = {
                'carbs': {'consumed': 0, 'target': 182, 'percentage': 0, 'remaining': 182},
                'protein': {'consumed': 0, 'target': 81, 'percentage': 0, 'remaining': 81},
                'fat': {'consumed': 0, 'target': 63, 'percentage': 0, 'remaining': 63}
            }
            has_non_zero_net_calories = False
            net_calories_dates = []
            net_calories = []

        return render_template(
            'dashboard.html',
            food_form=food_form,
            exercise_form=exercise_form,
            weight_form=weight_form,
            progress_form=progress_form,
            profile_complete=profile_complete,
            meals=meals,
            exercises=exercises,
            liked_food_ids=liked_food_ids,
            liked_exercise_ids=liked_exercise_ids,
            selected_date=selected_date,
            selected_period=selected_period,
            total_calories_consumed=total_calories_consumed,
            stats=stats,
            macros=macros,
            has_non_zero_net_calories=has_non_zero_net_calories,
            net_calories_dates=net_calories_dates,
            net_calories_values=net_calories,
            fitness_score=fitness_score,
            fitness_recommendations=fitness_recommendations
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Dashboard failed to load. Please try again.', 'error')
        return render_template('dashboard.html', **default_dashboard_args())

@app.route('/plan')
@login_required
def plan():
    try:
        weight_plan = generate_weight_plan(current_user)
        return render_template('plan.html', weight_plan=weight_plan)
    except Exception as e:
        logger.error(f"Plan error: {e}")
        flash('Failed to load plan. Please try again.', 'error')
        return render_template('plan.html', weight_plan={
            'calorie_target': 1500,
            'exercise_plan': "Error loading plan.",
            'meal_plan': "Error loading plan.",
            'timeline': "N/A"
        })

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    try:
        item_id = request.form.get('item_id')
        item_type = request.form.get('item_type')
        rating = request.form.get('rating')
        if item_id and item_type in ['food', 'exercise'] and rating in ['like', 'dislike']:
            db.session.query(Feedback).filter_by(user_id=current_user.id, item_id=item_id, item_type=item_type).delete()
            feedback = Feedback(user_id=current_user.id, item_id=item_id, item_type=item_type, rating=rating)
            db.session.add(feedback)
            db.session.commit()
            flash(f'{rating.capitalize()} recorded!', 'success')
        else:
            flash('Invalid feedback.', 'error')
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        flash('Failed to record feedback.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/debug_db')
@login_required
def debug_db():
    try:
        foods = Food.query.all()
        exercises = Exercise.query.all()
        return jsonify({
            'food_count': len(foods),
            'foods': [{'id': f.id, 'name': f.name, 'vegetarian': f.vegetarian} for f in foods],
            'exercise_count': len(exercises),
            'exercises': [{'id': e.id, 'name': e.name, 'type': e.type} for e in exercises]
        })
    except Exception as e:
        logger.error(f"Debug DB error: {e}")
        return jsonify({'error': str(e)})

# Initialize database
with app.app_context():
    try:
        init_db()
    except Exception as e:
        logger.error(f"Initial database setup failed: {e}")
        print(f"Initial database setup failed: {e}")

if __name__ == '__main__':
    import socket
    try:
        # Get local IP address for network access
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a public server to get local IP
        local_ip = s.getsockname()[0]
        s.close()
        print(f"Running on local host: http://127.0.0.1:5000")
        print(f"Running on network : http://{local_ip}:5000")
    except Exception as e:
        print(f"Error getting local IP: {e}")
        local_ip = "127.0.0.1"  # Fallback to localhost
        print(f"Running on local host only: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)