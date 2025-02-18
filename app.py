from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user, current_user
import hashlib

app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pub.db'
app.config['SQLALCHEMY_BINDS'] = {
    'recipe': 'sqlite:///base_of_recipe.db',
    'users': 'sqlite:///base_of_users.db',
    'public_recipes': 'sqlite:///pub.db',
    'likes': 'sqlite:///likes.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'nvkjdrbzriug5ueb54kj5tgbui4lbgn45hjb456jhbg45jh'
db = SQLAlchemy(app)

login_manager = LoginManager(app)


class User(db.Model, UserMixin):
    __bind_key__ = 'users'
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.now())
    pseudo = db.Column(db.Text, nullable=False, unique=True)

    def __repr__(self):
        return f'<User {self.id}>'


class Public_recipes(db.Model):
    __bind_key__ = 'public_recipes'
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    portions = db.Column(db.Integer, nullable=False)
    time_of_cook = db.Column(db.String(100), nullable=False)
    kall = db.Column(db.String(100), nullable=False)
    belok = db.Column(db.String(100), nullable=False)
    fat = db.Column(db.String(100), nullable=False)
    carb = db.Column(db.String(100), nullable=False)
    manual = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String, nullable=False)
    like = db.Column(db.Integer, nullable=False)
    ingredients = db.relationship('Ingredient', backref='recipe', lazy=True, cascade="all, delete-orphan")

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Public_recipes {self.name}>'


class Ingredient(db.Model):
    __bind_key__ = 'public_recipes'
    __tablename__ = 'ingredients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)

    def __repr__(self):
        return f'<Ingredient {self.name} - {self.quantity}>'


# создаем структуру для базы данных
class UserRecipeLike(db.Model):
    __bind_key__ = 'likes'  # Привязка к базе данных лайков
    __tablename__ = 'user_recipe_likes'

    id = db.Column(db.Integer, primary_key=True)
    usre = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<UserRecipeLike user_id={self.user_id} recipe_id={self.recipe_id}>'

class Recipe(db.Model):
    __bind_key__ = 'recipe'
    __tablename__ = 'recipe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    ingredients = db.Column(db.String(10), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.now())

    def __repr__(self):
        return f'<Recipe {self.id}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/all/<name>', methods=['POST', 'GET'])
def index(name):
    base = {
        'zavtraki': 'Завтраки',
        'bulion': 'Бульоны',
        'zakuski': 'Закузки',
        'napitki': 'Напитки',
        'osnovblud': 'Основные блюда',
        'pastapizza': 'Пасты и Пиццы',
        'rizzoto': 'Ризотто',
        'salati': 'Салаты',
        'souse': 'Соусы и Маринады ',
        'soup': 'Супы',
        'sandwich': 'Сендвичи',
        'vipechka': 'Выпечка и Десерты',
        'zagotovki': 'Заготовки'
    }
    # Проверяем, существует ли категория
    if name not in base:
        return render_template('index.html', recipes=[], message="Неверная категория")

    # Параметры пагинации
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Количество рецептов на одной странице

    if request.method == 'POST':
        # Получаем поисковый запрос
        search_term = request.form.get('search_n', '').strip()
        if not search_term:
            return render_template('index.html', recipes=[], message="Введите поисковый запрос", name=name)

        # Поиск рецептов с учетом категории и поискового запроса
        # Разделяем строку поиска на слова
        search_terms = search_term.split()  # Разбиваем строку на слова

        # Преобразуем все поля и значения в нижний регистр
        filter_conditions = [
            Public_recipes.name.ilike(f"%{search_term.lower()}%"),
            Ingredient.name.ilike(f"%{search_term.lower()}%")
        ]

        recipes = (
            db.session.query(Public_recipes)
            .join(Ingredient, Public_recipes.id == Ingredient.recipe_id)  # соединение таблиц
            .filter(*filter_conditions)  # Применяем все условия фильтрации
            .order_by(Public_recipes.like.desc())  # Сортировка по длине названия рецепта
            .paginate(page=page, per_page=per_page)
        )

        return render_template(
            'index.html',
            recipes=recipes.items,
            total_pages=recipes.pages,
            name=name,
            search_term=search_term
        )

    # Если GET-запрос, показываем рецепты по категории
    recipes = Public_recipes.query.filter(Public_recipes.kind == base[name]).order_by(Public_recipes.like.desc()).paginate(page=page, per_page=per_page)

    # Если запрос AJAX, рендерим только список рецептов
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('recipes_partial.html', recipes=recipes.items, name=name)

    # Если обычный запрос, рендерим всю страницу
    return render_template(
        'index.html',
        recipes=recipes.items,
        total_pages=recipes.pages,
        name=name
    )


# страница регистрации
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        session.pop('_flashes', None)  # очищаем всплывающие сообщения
        # проверка есть ли почта в базе данных
        if not User.query.filter_by(email=request.form['email']).first():

            # проверка требований пароля
            if request.form["password1"] == request.form["password"] and \
                    len(request.form['password']) > 4:
                email = request.form['email'] # получаем введенную почту

                # хеширование пароля
                hash = generate_password_hash(request.form['password'])

                # генерация "id" пользователя
                pseudo = generate_pseudonym(email)

                # проверка есть ли такой же хэш с "id" пользователя
                if User.query.filter_by(pseudo=pseudo).first():
                    while True:
                        pseudo = generate_pseudonym(email)
                        if not User.query.filter_by(pseudo=pseudo).first():
                            break
                user = User(email=email, password=hash, pseudo=pseudo)
                db.session.add(user) # добавляем информацию о пользователе
                db.session.commit() # обновляем базу данных
                flash("Вы успешно зарегистрированы", "success")
                return redirect('/user')
            else:
                flash("Неверно заполнены поля", "error")
        else:
            flash("Этот email уже зарегистрирован", "error")
    return render_template('register.html')


# если страница не найдена
@app.route('/None')
def No():
    return redirect('/all')


@app.route('/')
def dd():
    return redirect('/all/zavtraki')


# вход в аккаунт
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    session.pop('_flashes', None)
    if not current_user.is_authenticated:
        flash('Выполните вход')

    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            user = User.query.filter_by(email=email).first()
            if check_password_hash(user.password, password):
                login_user(user)

                next_page = request.args.get('next')
                session.pop('_flashes', None)

                return redirect(next_page)
            else:
                flash('Неправильный email или пароль')
        except:
            flash('Неправильный email или пароль')

    return render_template('login.html')


# выход из аккаунта
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/user')


# страница с информацией о пользователе
@app.route('/user', methods=['POST', 'GET'])
@login_required
def user():
    return render_template('user.html')


# открытие рецепта пользователя
@app.route('/recipe/<pseudo>/<int:id>', methods=['GET', 'POST'])
def recipe_detail(pseudo, id):
    recipe = Recipe.query.get_or_404(id)

    # чтобы человек не мог зайти на чужой рецепт
    if recipe.owner != current_user.pseudo:
        flash('У вас нет доступа к этому рецепту.', 'error')
        return redirect('/menu')

    if request.method == 'POST':
        recipe.name = request.form['name']
        recipe.ingredients = request.form['ingredients']
        recipe.description = request.form['description']

        try:
            db.session.commit()
            flash('Успешное редактирование')
            return redirect(f'/recipe/{current_user.pseudo}/{id}')
        except:
            flash('Не удалось редактировать')
            return redirect(f'/recipe/{current_user.pseudo}/{id}')
    else:
        return render_template('recipe_detail.html', recipe=recipe, pseudo=current_user.pseudo)


# удаление
@app.route('/recipe/<pseudo>/<int:id>/del')
def recipe_delete(id, pseudo):
    recipe = Recipe.query.get_or_404(id)
    if not recipe:
        flash('Рецепт не найден')
        return redirect(f'/menu/{current_user.pseudo}')
    try:
        db.session.delete(recipe)
        db.session.commit()
        flash('Успешно удалено')
        return redirect(f'/menu/{current_user.pseudo}')

    except:
        flash('Не удалось удалить')
        return redirect(f'/menu/{current_user.pseudo}')



@app.route('/all/<kind>/<int:id>', methods=['POST', 'GET'])
@login_required
def recipe_public(kind, id):
    recipe = Public_recipes.query.get_or_404(id)
    cur = current_user.id
    rec = recipe.id
    print(cur,rec)
    if request.method == 'POST':
        if f'{cur} {rec}' in [x.usre for x in UserRecipeLike.query.all()]:
            flash('Вы уже поставили лайк для этого рецепта')
        else:
            l = UserRecipeLike(usre=f'{cur} {rec}')
            db.session.add(l)
            recipe.like += 1
            db.session.commit()
    return render_template('recipe_pub.html', recipe=recipe, name=kind)

@app.route('/menu/ind/rec/<int:id>', methods=['POST', 'GET'])
@login_required
def recipe_public_ind(id):
    recipe = Public_recipes.query.get_or_404(id)
    return render_template('recipe_ind.html', recipe=recipe, pseudo=current_user.pseudo)

@app.route('/menu/')
@login_required
def menu_for_unlog():
    pseudo = current_user.pseudo
    return redirect(f'{pseudo}')


@app.route('/menu/<pseudo>', methods=['GET', 'POST'])
@login_required
def menu(pseudo):
    if pseudo != current_user.pseudo:
        flash('У вас нет доступа к этому меню.', 'error')
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        ingredients = request.form['ingredients']
        description = request.form['description']
        owner = current_user.pseudo
        recipe = Recipe(name=name, ingredients=ingredients, owner=owner, description=description)

        try:
            db.session.add(recipe)
            db.session.commit()
            flash("Рецепт успешно создан")
            return redirect(f'/menu/{current_user.pseudo}')
        except:
            flash('Не удалось создать рецепт')
            return redirect(f'/menu/{current_user.pseudo}')

    else:
        recipe = Recipe.query.filter_by(owner=current_user.pseudo).order_by(Recipe.id.desc()).all()
        return render_template('menu.html', recipe=recipe, pseudo=pseudo)

@app.route('/menu/ind/<pseudo>', methods=['GET', 'POST'])
@login_required
def menu_ind(pseudo):
    if pseudo != current_user.pseudo:
        flash('У вас нет доступа к этому меню.', 'error')
        return redirect('/')
    else:
        list = []
        for i in [x.usre.split() for x in UserRecipeLike.query.all()]:
            if current_user.id == int(i[0]):
                list.append(Public_recipes.query.get_or_404(i[1]))
        return render_template('menu_lile.html', recipes=list, pseudo=pseudo)
@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect('/login' + '?next=' + request.url)
    return response


def generate_pseudonym(username):
    hash_object = hashlib.md5(username.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig[:16]


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
