import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# --- SETUP ---
basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'Database')
if not os.path.exists(db_dir): os.makedirs(db_dir)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kannel-pro-secure-112233'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_dir, 'kannel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class DogParent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); role = db.Column(db.String(20)) 
    breed = db.Column(db.String(100)); achievements = db.Column(db.String(200))
    health_status = db.Column(db.String(100)); bio = db.Column(db.Text)

class Puppy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50)); breed = db.Column(db.String(100))
    gender = db.Column(db.String(10)); is_available = db.Column(db.Boolean, default=True)
    price = db.Column(db.Float)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100))
    pup_interest = db.Column(db.String(50))
    breed = db.Column(db.String(50))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client = db.Column(db.String(100)); pup_name = db.Column(db.String(50))
    gender = db.Column(db.String(10)); breed = db.Column(db.String(50))
    payment = db.Column(db.Float); contract = db.Column(db.String(20))

class VetVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_name = db.Column(db.String(100)); visit_type = db.Column(db.String(50))
    date = db.Column(db.String(20)); cost = db.Column(db.Float); notes = db.Column(db.Text)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50)); description = db.Column(db.String(200))
    amount = db.Column(db.Float); date = db.Column(db.String(20))

class Dog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); birth_date = db.Column(db.Date)
    breed = db.Column(db.String(100)); food_type = db.Column(db.String(100))
    schedule = db.Column(db.String(100))
    def get_age(self):
        if not self.birth_date: return "N/A"
        today = date.today()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return f"{age} yrs" if age > 0 else "Puppy"

class Breeding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dam_name = db.Column(db.String(100)); sire_name = db.Column(db.String(100))
    mating_date = db.Column(db.Date); due_date = db.Column(db.Date); status = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user); return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('home'))

@app.route('/')
def home(): return render_template('index.html')

@app.route('/parents', methods=['GET', 'POST'])
def parents():
    if request.method == 'POST' and current_user.is_authenticated:
        p = DogParent(name=request.form['name'], role=request.form['role'], breed=request.form['breed'], achievements=request.form['achievements'], health_status=request.form['health_status'], bio=request.form['bio'])
        db.session.add(p); db.session.commit(); return redirect('/parents')
    return render_template('parents.html', sires=DogParent.query.filter_by(role='Sire').all(), dams=DogParent.query.filter_by(role='Dam').all())

@app.route('/puppies')
def puppies_public(): return render_template('puppies.html', puppies=Puppy.query.all())

@app.route('/admin/puppies', methods=['GET', 'POST'])
@login_required
def puppies_admin():
    if request.method == 'POST':
        new_pup = Puppy(name=request.form['name'], breed=request.form['breed'], gender=request.form['gender'], price=float(request.form['price']))
        db.session.add(new_pup); db.session.commit(); return redirect('/admin/puppies')
    return render_template('puppies_admin.html', puppies=Puppy.query.all())

@app.route('/reserve/<int:pup_id>')
def reserve_pup(pup_id):
    p = Puppy.query.get_or_404(pup_id)
    return redirect(url_for('sales', pup_name=p.name, breed=p.breed))

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if request.method == 'POST':
        if current_user.is_authenticated:
            # Admin adding direct sale
            s = Sale(client=request.form['client'], pup_name=request.form['pup_name'], breed=request.form['breed'], payment=float(request.form['payment']), contract=request.form['contract'])
            db.session.add(s)
        else:
            # User applying
            a = Application(client_name=request.form['client_name'], pup_interest=request.form['pup_name'], breed=request.form['breed'], message=request.form['message'])
            db.session.add(a)
        db.session.commit(); return redirect('/sales')
    
    apps = Application.query.filter_by(status="Pending").all() if current_user.is_authenticated else []
    return render_template('sales.html', sales=Sale.query.all(), apps=apps)

@app.route('/approve/<int:app_id>/<string:action>')
@login_required
def handle_app(app_id, action):
    a = Application.query.get_or_404(app_id)
    if action == 'approve':
        new_s = Sale(client=a.client_name, pup_name=a.pup_interest, breed=a.breed, payment=0.0, contract="Pending")
        db.session.add(new_s); a.status = "Approved"
    else:
        a.status = "Declined"
    db.session.commit(); return redirect('/sales')

@app.route('/vet', methods=['GET', 'POST'])
def vet():
    if request.method == 'POST' and current_user.is_authenticated:
        v = VetVisit(dog_name=request.form['dog_name'], visit_type=request.form['type'], date=request.form['date'], cost=float(request.form['cost']), notes=request.form['notes'])
        db.session.add(v); db.session.commit(); return redirect('/vet')
    return render_template('vet.html', visits=VetVisit.query.all())

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    if request.method == 'POST':
        e = Expense(category=request.form['category'], description=request.form['description'], amount=float(request.form['amount']), date=request.form['date'])
        db.session.add(e); db.session.commit(); return redirect('/expenses')
    exps = Expense.query.all(); return render_template('expenses.html', expenses=exps, total=sum(i.amount for i in exps))

@app.route('/breeding', methods=['GET', 'POST'])
def breeding():
    if request.method == 'POST' and current_user.is_authenticated:
        m_dt = datetime.strptime(request.form['mating_date'], '%Y-%m-%d').date()
        b = Breeding(dam_name=request.form['dam_name'], sire_name=request.form['sire_name'], mating_date=m_dt, due_date=m_dt+timedelta(days=63), status="Pending")
        db.session.add(b); db.session.commit(); return redirect('/breeding')
    return render_template('breeding.html', records=Breeding.query.all())

@app.route('/feeding', methods=['GET', 'POST'])
@login_required
def feeding():
    if request.method == 'POST':
        b_dt = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
        d = Dog(name=request.form['name'], birth_date=b_dt, breed=request.form['breed'], food_type=request.form['food'], schedule=request.form['schedule'])
        db.session.add(d); db.session.commit(); return redirect('/feeding')
    return render_template('feeding.html', dogs=Dog.query.all())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('kannel123', method='pbkdf2:sha256')))
            db.session.commit()
    app.run(debug=True)