from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm
from models import db, User, ForumPost, Product, Cart
from config import Config
from datetime import datetime

# ------------------- APP INITIALIZATION -------------------

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Create database tables if they do not exist
with app.app_context():
    db.create_all()
    # Add agriculture sample products if none exist
    if Product.query.count() == 0:
        sample_products = [
            Product(
                name='Organic Tomatoes', 
                category='Vegetables', 
                price=3.99, 
                image='https://images.unsplash.com/photo-1546470427-e212d4d25323?w=400',
                description='Fresh organic tomatoes grown without pesticides, perfect for salads and cooking.',
                stock=50
            ),
            Product(
                name='Fresh Apples', 
                category='Fruits', 
                price=2.49, 
                image='https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?w=400',
                description='Crisp and juicy red apples, hand-picked from our orchard.',
                stock=75
            ),
            Product(
                name='Whole Wheat Flour', 
                category='Grains', 
                price=4.99, 
                image='https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400',
                description='Stone-ground whole wheat flour from organic wheat grains.',
                stock=30
            ),
            Product(
                name='Farm Fresh Eggs', 
                category='Dairy', 
                price=5.99, 
                image='https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400',
                description='Free-range eggs from happy chickens raised on natural feed.',
                stock=40
            ),
            Product(
                name='Organic Spinach', 
                category='Organic', 
                price=2.99, 
                image='https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400',
                description='Tender organic spinach leaves, packed with nutrients.',
                stock=60
            ),
            Product(
                name='Garden Shovel', 
                category='Farm Tools', 
                price=24.99, 
                image='https://images.unsplash.com/photo-1572984334707-0c0df46957a9?w=400',
                description='Durable steel garden shovel perfect for all your farming needs.',
                stock=15
            )
        ]
        for product in sample_products:
            db.session.add(product)
        db.session.commit()
        print("✅ Agriculture sample products added to database!")


# ------------------- ROUTES -------------------

# Home Page
@app.route('/')
def home():
    return render_template('home.html')


# ------------------- USER AUTH -------------------

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please log in.')
            return redirect(url_for('login'))

        hashed = generate_password_hash(form.password.data)
        user = User(name=form.name.data, email=form.email.data, password=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session['user'] = user.id
            session['name'] = user.name
            session['role'] = user.role
            flash('Welcome back!')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html', form=form)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('home'))


# ------------------- PROFILE -------------------

@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please log in to view your profile.')
        return redirect(url_for('login'))
    return render_template('profile.html')


# ------------------- FORUM -------------------

@app.route('/forum')
def forum():
    posts = ForumPost.query.all()
    return render_template('forum.html', posts=posts)


@app.route('/add_post', methods=['POST'])
def add_post():
    if 'user' not in session:
        flash('You must be logged in to post.')
        return redirect(url_for('login'))

    title = request.form.get('title')
    content = request.form.get('content')

    if title and content:
        post = ForumPost(title=title, content=content, user_id=session['user'])
        db.session.add(post)
        db.session.commit()
        flash('Post added successfully!')
    else:
        flash('Please enter a title and content.')

    return redirect(url_for('forum'))


# ------------------- SHOP -------------------

@app.route('/shop')
def shop():
    products = Product.query.all()
    return render_template('shop.html', products=products)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    product = Product.query.get_or_404(product_id)

    # Enhanced cart logic (session-based with duplicate handling)
    cart = session.get('cart', {})
    
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'quantity': quantity,
            'image': product.image
        }
    
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'message': f'{product.name} added to cart!', 'cart_count': len(cart)})


@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    cart_items = list(cart.values())
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)


@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        product_name = cart[product_id_str]['name']
        del cart[product_id_str]
        session['cart'] = cart
        session.modified = True
    
    return jsonify({'success': True, 'message': f'{product_name} removed from cart!'})


# ------------------- SHOP API ROUTES (For Dynamic Operations) -------------------

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        products_data = []
        for product in products:
            product_data = {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': product.price,
                'image': product.image,
                'seller_id': product.seller_id
            }
            # Safely add description and stock if they exist
            if hasattr(product, 'description') and product.description:
                product_data['description'] = product.description
            if hasattr(product, 'stock') and product.stock is not None:
                product_data['stock'] = product.stock
            if hasattr(product, 'origin') and product.origin:
                product_data['origin'] = product.origin
                
            products_data.append(product_data)
        return jsonify(products_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/products', methods=['POST'])
def api_add_product():
    try:
        data = request.get_json()
        
        # Create product with basic fields
        product_data = {
            'name': data['name'],
            'category': data['category'],
            'price': float(data['price']),
            'image': data.get('image', 'https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400&q=80'),
            'seller_id': session.get('user', 1)  # Use session user or default
        }
        
        # Add optional fields
        if 'description' in data:
            product_data['description'] = data['description']
        if 'stock' in data:
            product_data['stock'] = int(data['stock'])
        if 'origin' in data:
            product_data['origin'] = data['origin']
            
        new_product = Product(**product_data)
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Product added successfully!', 
            'id': new_product.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 400


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        # Update basic fields
        product.name = data['name']
        product.category = data['category']
        product.price = float(data['price'])
        
        # Update image if provided
        if 'image' in data:
            product.image = data['image']
            
        # Update optional fields
        if 'description' in data:
            product.description = data['description']
        if 'stock' in data:
            product.stock = int(data['stock'])
        if 'origin' in data:
            product.origin = data['origin']
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Product updated successfully!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 400


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        product_name = product.name
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Product "{product_name}" deleted successfully!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 400


@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    try:
        cart = session.get('cart', {})
        cart_items = []
        total = 0
        
        for product_id, item in cart.items():
            product = Product.query.get(int(product_id))
            if product:
                subtotal = item['price'] * item['quantity']
                cart_items.append({
                    'id': product.id,
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': item['quantity'],
                    'subtotal': subtotal,
                    'image': item.get('image', 'https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400&q=80')
                })
                total += subtotal
        
        return jsonify({
            'success': True,
            'items': cart_items, 
            'total': total,
            'cart_count': len(cart)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/cart', methods=['POST'])
def api_add_to_cart():
    try:
        data = request.get_json()
        product_id = data['product_id']
        quantity = data.get('quantity', 1)
        
        product = Product.query.get_or_404(product_id)
        
        cart = session.get('cart', {})
        
        if str(product_id) in cart:
            cart[str(product_id)]['quantity'] += quantity
        else:
            cart[str(product_id)] = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity,
                'image': product.image
            }
        
        session['cart'] = cart
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': f'{product.name} added to cart!', 
            'cart_count': len(cart)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
def api_remove_from_cart(product_id):
    try:
        cart = session.get('cart', {})
        product_id_str = str(product_id)
        
        if product_id_str in cart:
            product_name = cart[product_id_str]['name']
            del cart[product_id_str]
            session['cart'] = cart
            session.modified = True
            
            return jsonify({
                'success': True,
                'message': f'{product_name} removed from cart!',
                'cart_count': len(cart)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Product not found in cart'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ------------------- CONSULTANCY & KNOWLEDGE -------------------

@app.route('/consultancy')
def consultancy():
    return render_template('consultancy.html')


@app.route('/knowledge')
def knowledge():
    return render_template('knowledge.html')


# ------------------- ADMIN DASHBOARD -------------------

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        flash('Please log in as admin.')
        return redirect(url_for('login'))

    users = User.query.all()
    products = Product.query.all()
    return render_template('admin_dashboard.html', users=users, products=products)


# ------------------- RUN APP -------------------

@app.route('/test_session')
def test_session():
    session['test_value'] = 'working!'
    return f"Session set! Value = {session.get('test_value')}"

if __name__ == '__main__':
    app.run(debug=True)