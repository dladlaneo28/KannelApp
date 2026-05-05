import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
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
    is_approved = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)

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
    amount = db.Column(db.Float, default=0.0)
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

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)

class PetShopOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100))
    total_price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Pending")
    date = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('PetShopOrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class PetShopOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('pet_shop_order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    price_at_time = db.Column(db.Float)
    product = db.relationship('Product')

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100))
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        
        # Check if first user
        is_first = User.query.count() == 0
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
            
        new_user = User(
            username=username, 
            password=password, 
            is_approved=is_first, 
            is_superuser=is_first
        )
        db.session.add(new_user)
        db.session.commit()
        
        if is_first:
            flash('Registration successful! You are the superuser. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration successful! Please wait for the superuser to approve your account.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not current_user.is_superuser:
        return "Access Denied: Superusers only.", 403
        
    pending_users = User.query.filter_by(is_superuser=False).all()
    approved_users = User.query.filter_by(is_superuser=True).all()
    return render_template('admin_users.html', pending=pending_users, approved=approved_users)

@app.route('/admin/users/approve/<int:user_id>')
@login_required
def approve_user(user_id):
    if not current_user.is_superuser:
        return "Access Denied.", 403
    u = User.query.get_or_404(user_id)
    u.is_approved = True
    u.is_superuser = True
    db.session.commit()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_superuser:
        return "Access Denied.", 403
    u = User.query.get_or_404(user_id)
    if u.id != current_user.id:
        db.session.delete(u)
        db.session.commit()
    return redirect(url_for('admin_users'))

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('home'))

@app.route('/')
def home(): return render_template('landing.html')

@app.route('/kennel')
def kennel(): return render_template('index.html')

@app.route('/petshop')
def petshop():
    products = Product.query.filter(Product.stock > 0).all()
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template('petshop.html', products=products, cart_count=cart_count)

@app.route('/petshop/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        cart[product_id_str] += quantity
    else:
        cart[product_id_str] = quantity
    session['cart'] = cart
    flash('Added to cart!', 'success')
    return redirect(url_for('petshop'))

@app.route('/petshop/cart', methods=['GET', 'POST'])
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0.0
    for pid_str, qty in cart.items():
        prod = Product.query.get(int(pid_str))
        if prod:
            subtotal = prod.price * qty
            total += subtotal
            cart_items.append({'product': prod, 'quantity': qty, 'subtotal': subtotal})
            
    if request.method == 'POST':
        client_name = request.form['client_name']
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('petshop'))
            
        new_order = PetShopOrder(client_name=client_name, total_price=total)
        db.session.add(new_order)
        db.session.flush() # Get order ID
        
        for item in cart_items:
            order_item = PetShopOrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price_at_time=item['product'].price
            )
            db.session.add(order_item)
            
        db.session.commit()
        session.pop('cart', None)
        flash(f'Order placed successfully! Your Order ID is {new_order.id}.', 'success')
        return redirect(url_for('petshop'))
        
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/petshop/cart/clear')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('petshop'))

@app.route('/admin/petshop', methods=['GET', 'POST'])
@login_required
def petshop_admin():
    if not current_user.is_superuser:
        return "Access Denied", 403
    if request.method == 'POST':
        name = request.form['name'].strip()
        existing = Product.query.filter(db.func.lower(Product.name) == db.func.lower(name)).first()
        if existing:
            existing.stock += int(request.form['stock'])
        else:
            new_prod = Product(name=name, description=request.form['description'], price=float(request.form['price']), stock=int(request.form['stock']))
            db.session.add(new_prod)
        db.session.commit()
        return redirect(url_for('petshop_admin'))
    products = Product.query.all()
    orders = PetShopOrder.query.all()
    return render_template('petshop_admin.html', products=products, orders=orders)

@app.route('/admin/petshop/order/<int:order_id>/<string:action>')
@login_required
def handle_petshop_order(order_id, action):
    if not current_user.is_superuser:
        return "Access Denied", 403
    order = PetShopOrder.query.get_or_404(order_id)
    if action == 'approve' and order.status == 'Pending':
        can_fulfill = True
        for item in order.items:
            if item.product.stock < item.quantity:
                can_fulfill = False
                break
                
        if can_fulfill:
            for item in order.items:
                item.product.stock -= item.quantity
            order.status = 'Approved'
            new_income = Income(source=f"PetShop Order #{order.id} - {order.client_name}", amount=order.total_price)
            db.session.add(new_income)
        else:
            flash('Not enough stock to fulfill this order.', 'error')
    elif action == 'decline':
        order.status = 'Declined'
    db.session.commit()
    return redirect(url_for('petshop_admin'))

@app.route('/cancel_app/<int:app_id>')
def cancel_app(app_id):
    a = Application.query.get_or_404(app_id)
    # We could check if current user matches client_name, but we don't have client accounts yet.
    # We'll just allow cancellation if it's pending.
    if a.status == "Pending":
        a.status = "Cancelled"
        db.session.commit()
    return redirect(url_for('sales'))

@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    o = PetShopOrder.query.get_or_404(order_id)
    if o.status == "Pending":
        o.status = "Cancelled"
        db.session.commit()
    return redirect(url_for('petshop'))

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
    if not current_user.is_superuser:
        return "Access Denied", 403
    if request.method == 'POST':
        new_pup = Puppy(name=request.form['name'], breed=request.form['breed'], gender=request.form['gender'], price=float(request.form['price']))
        db.session.add(new_pup); db.session.commit(); return redirect('/admin/puppies')
    return render_template('puppies_admin.html', puppies=Puppy.query.all())

@app.route('/reserve/<int:pup_id>')
@login_required
def reserve_pup(pup_id):
    p = Puppy.query.get_or_404(pup_id)
    return redirect(url_for('sales', pup_name=p.name, breed=p.breed))

@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':
        if current_user.is_superuser:
            # Admin adding direct sale
            s = Sale(client=request.form['client'], pup_name=request.form['pup_name'], breed=request.form['breed'], payment=float(request.form['payment']), contract=request.form['contract'])
            db.session.add(s)
        else:
            # User applying
            a = Application(client_name=request.form['client_name'], pup_interest=request.form['pup_name'], breed=request.form['breed'], message=request.form['message'], amount=float(request.form.get('amount', 0.0)))
            db.session.add(a)
        db.session.commit(); return redirect('/sales')
    
    if current_user.is_superuser:
        apps = Application.query.filter_by(status="Pending").all()
    else:
        apps = Application.query.filter_by(client_name=current_user.username).all()
        
    return render_template('sales.html', sales=Sale.query.all(), apps=apps)

@app.route('/approve/<int:app_id>/<string:action>')
@login_required
def handle_app(app_id, action):
    if not current_user.is_superuser:
        return "Access Denied", 403
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
    if not current_user.is_superuser:
        return "Access Denied", 403
    if request.method == 'POST':
        e = Expense(category=request.form['category'], description=request.form['description'], amount=float(request.form['amount']), date=request.form['date'])
        db.session.add(e); db.session.commit(); return redirect('/expenses')
    exps = Expense.query.all()
    incomes = Income.query.all()
    total_exp = sum(i.amount for i in exps)
    total_inc = sum(i.amount for i in incomes)
    profit = total_inc - total_exp
    return render_template('expenses.html', expenses=exps, incomes=incomes, total_exp=total_exp, total_inc=total_inc, profit=profit)

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
    if not current_user.is_superuser:
        return "Access Denied", 403
    if request.method == 'POST':
        b_dt = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
        d = Dog(name=request.form['name'], birth_date=b_dt, breed=request.form['breed'], food_type=request.form['food'], schedule=request.form['schedule'])
        db.session.add(d); db.session.commit(); return redirect('/feeding')
    return render_template('feeding.html', dogs=Dog.query.all())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)