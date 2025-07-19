from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json
import os
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  

app = Flask(__name__)
app.secret_key = 'admin_super_secret_key'

@app.route("/api/products")
def get_products():
    with open("products.json", "r", encoding="utf-8") as f:
        products = json.load(f)
    return jsonify(products)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAIN_WEB_URL = 'http://127.0.0.1:5000'
MAIN_WEB_UPLOAD_API = f"{MAIN_WEB_URL}/api/upload_product_image"
MAIN_WEB_UPLOAD_AVATAR_API = f"{MAIN_WEB_URL}/api/upload_shop_avatar"
MAIN_WEB_UPDATE_SHOP_INFO_API = f"{MAIN_WEB_URL}/api/update_shop_info"
# MAIN_WEB_GET_SHOP_INFO_API = f"{MAIN_WEB_URL}/get_shop_info" # Không cần nữa

# ==== ADMIN USERS ====
ADMIN_USERS_FILE = 'admin_users.json'

def load_admin_users():
    if os.path.exists(ADMIN_USERS_FILE):
        with open(ADMIN_USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_admin_users(admin_users):
    with open(ADMIN_USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admin_users, f, indent=2, ensure_ascii=False)

# ==== KIỂM TRA ĐĂNG NHẬP ADMIN ====
def is_admin_logged_in():
    return 'admin_user' in session

@app.context_processor
def inject_admin_user():
    return {'admin_user': session.get('admin_user')}

categories = [
    {"id": 1, "name": "Thời trang nam", "slug": "thoitrang-nam"},
    {"id": 2, "name": "Thời trang nữ", "slug": "thoitrang-nu"},
    {"id": 3, "name": "Điện thoại", "slug": "dien-thoai"},
    {"id": 4, "name": "Thiết bị điện tử", "slug": "dien-tu"},
    {"id": 5, "name": "Máy tính & Laptop", "slug": "may-tinh"},
    {"id": 6, "name": "Đồ gia dụng", "slug": "dogia-dung"},
    {"id": 7, "name": "Giày dép", "slug": "giay-dep"},
    {"id": 8, "name": "Sức khỏe", "slug": "suc-khoe"},
    {"id": 9, "name": "Đồ chơi & Sở thích", "slug": "do-choi"},
    {"id": 10, "name": "Thể thao & Outdoor", "slug": "the-thao"},
    {"id": 11, "name": "Thú cưng", "slug": "thu-cung"},
    {"id": 12, "name": "Mẹ và bé", "slug": "meva-be"},
    {"id": 13, "name": "Nhà cửa & đời sống", "slug": "nha-cua"},
    {"id": 14, "name": "Phụ kiện", "slug": "phu-kien"},
    {"id": 15, "name": "Nội thất", "slug": "noi-that"},
    {"id": 16, "name": "Mỹ phẩm", "slug": "my-pham"},
    {"id": 17, "name": "Nhà sách online", "slug": "nha-sach"},
    {"id": 18, "name": "Khác", "slug": "khac"},
]

# ==== THÔNG TIN WEB (SHOP INFO) - ADMIN WEB SẼ QUẢN LÝ DỮ LIỆU RIÊNG TRONG admin_users.json ====
def load_current_admin_shop_info():
    admin_users = load_admin_users()
    current_admin_user = session.get('admin_user')
    if current_admin_user and current_admin_user in admin_users:
        return admin_users[current_admin_user].get("shop_info", {
            "shop_name": "Tên Shop Của Bạn",
            "hotline": "1900 1234",
            "email": "info@yourshop.com",
            "address": "Địa chỉ cửa hàng của bạn",
            "facebook_link": "",
            "zalo_link": "",
            "website_link": "",
            "shop_avatar": "default_shop_avatar.png",
            "info_set": False # THÊM TRƯỜNG MỚI ĐỂ ĐÁNH DẤU ĐÃ NHẬP THÔNG TIN HAY CHƯA
        })
    return { # Trả về mặc định nếu không có admin đăng nhập
        "shop_name": "Shop của bạn", "hotline": "", "email": "", "address": "",
        "facebook_link": "", "zalo_link": "", "website_link": "",
        "shop_avatar": "default_shop_avatar.png", "info_set": False
    }


def save_current_admin_shop_info(shop_info_data):
    admin_users = load_admin_users()
    current_admin_user = session.get('admin_user')
    if current_admin_user and current_admin_user in admin_users:
        admin_users[current_admin_user]["shop_info"] = shop_info_data
        save_admin_users(admin_users)
        return True
    return False

@app.route('/')
def admin_home():
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để truy cập trang quản trị!", "warning")
        return redirect(url_for('login_admin'))

    # Lấy thông tin shop hiện tại
    shop_info = load_current_admin_shop_info()
    
    # Nếu shop chưa có thông tin, yêu cầu cập nhật
    if not shop_info.get('info_set', False):
        flash("Chào mừng! Vui lòng cập nhật thông tin cửa hàng của bạn để bắt đầu.", "info")
        return redirect(url_for('manage_shop_info'))

    # Lấy danh sách sản phẩm của shop từ Web Bán Hàng qua API
    seller_username = session.get('admin_user')
    products = []
    try:
        response = requests.get(f"{MAIN_WEB_URL}/api/get_products/{seller_username}")
        response.raise_for_status()  # Báo lỗi nếu request không thành công
        products = response.json()
    except requests.exceptions.ConnectionError:
        flash('Lỗi: Không thể kết nối đến Web Bán Hàng để lấy danh sách sản phẩm.', 'error')
    except Exception as e:
        flash(f'Lỗi không xác định khi lấy sản phẩm: {e}', 'error')

    return render_template(
        'index.html', 
        shop_info=shop_info, 
        products=products, 
        MAIN_WEB_URL=MAIN_WEB_URL
    )
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để thực hiện chức năng này!", "warning")
        return redirect(url_for('login_admin'))
    
    shop_info = load_current_admin_shop_info()
    if not shop_info.get('info_set', False):
        flash("Bạn cần cập nhật thông tin shop trước khi thêm sản phẩm!", "warning")
        return redirect(url_for('manage_shop_info'))

    if request.method == 'POST':
        # --- 1. Xử lý Upload nhiều ảnh ---
        image_files = request.files.getlist('images')
        uploaded_filenames = []
        for file in image_files:
            if file and file.filename != '':
                try:
                    # Gói file để gửi đi
                    files_to_upload = {'image': (secure_filename(file.filename), file.read(), file.mimetype)}
                    upload_response = requests.post(MAIN_WEB_UPLOAD_API, files=files_to_upload)
                    upload_response.raise_for_status()
                    
                    upload_result = upload_response.json()
                    if upload_result.get('success'):
                        uploaded_filenames.append(upload_result.get('filename'))
                    else:
                        flash(f"Lỗi khi upload ảnh: {upload_result.get('message')}", "error")
                except Exception as e:
                    flash(f"Lỗi hệ thống khi upload ảnh: {e}", "error")
                    return redirect(url_for('add_product'))

        # --- 2. Xử lý thông tin chung và các phiên bản ---
        seller_username = session.get('admin_user')
        
        # Lấy danh sách các thuộc tính của phiên bản từ form
        variant_colors = request.form.getlist('variant_color')
        variant_storages = request.form.getlist('variant_storage')
        variant_prices = request.form.getlist('variant_price')
        
        # Tạo danh sách các đối tượng 'variants'
        variants = []
        for i in range(len(variant_prices)):
            variants.append({
                "sku": f"SKU_{seller_username.upper()}_{i+1}", # Tạo SKU đơn giản
                "price": int(variant_prices[i]),
                "attributes": {
                    "Màu sắc": variant_colors[i],
                    "Dung lượng": variant_storages[i]
                }
            })

        # Tạo cấu trúc sản phẩm hoàn chỉnh theo mô hình dữ liệu mới
        new_product_data = {
            "name": request.form['name'],
            "description": request.form['description'],
            "category_slug": request.form['category_slug'],
            "seller_username": seller_username,
            "images": uploaded_filenames if uploaded_filenames else ["default.jpg"],
            "options": [
                {"name": "Màu sắc", "values": list(set(variant_colors))},
                {"name": "Dung lượng", "values": list(set(variant_storages))}
            ],
            "variants": variants
        }

        # --- 3. Gửi dữ liệu sản phẩm mới tới API của Web bán hàng ---
        try:
            response = requests.post(f"{MAIN_WEB_URL}/api/add_product", json=new_product_data)
            response.raise_for_status()
            result = response.json()
            if result.get('success'):
                flash(f'✅ Sản phẩm "{new_product_data["name"]}" đã được thêm thành công!', 'success')
                return redirect(url_for('manage_products'))
            else:
                flash(f'❗ Lỗi từ web chính: {result.get("message", "Không rõ lỗi")}', 'error')
        except Exception as e:
            flash(f'❌ Lỗi không xác định khi gửi sản phẩm: {e}', 'error')

        return redirect(url_for('add_product'))
    
    # Render trang add_product cho phương thức GET
    return render_template('add.html', categories=categories)
# ==== QUẢN LÝ THÔNG TIN WEB (SHOP INFO) ====
@app.route('/manage_shop_info', methods=['GET', 'POST'])
def manage_shop_info():
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để quản lý thông tin web!", "warning")
        return redirect(url_for('login_admin'))
    
    shop_info = load_current_admin_shop_info()

    # Nếu thông tin đã được thiết lập, chuyển hướng đến trang hiển thị
    if request.method == 'GET' and shop_info.get('info_set', False):
        return redirect(url_for('my_shop_info')) # CHUYỂN HƯỚNG TỚI TRANG HIỂN THỊ THÔNG TIN SHOP

    if request.method == 'POST':
        # Cập nhật thông tin shop từ form
        shop_info['shop_name'] = request.form['shop_name']
        shop_info['hotline'] = request.form['hotline']
        shop_info['email'] = request.form['email']
        shop_info['address'] = request.form['address']
        shop_info['facebook_link'] = request.form.get('facebook_link', '')
        shop_info['zalo_link'] = request.form.get('zalo_link', '')
        shop_info['website_link'] = request.form.get('website_link', '')
        
        # Đánh dấu là thông tin đã được thiết lập
        shop_info['info_set'] = True # ĐẶT info_set = True KHI CẬP NHẬT

        # Xử lý upload avatar shop
        avatar_filename = shop_info.get('shop_avatar', 'default_shop_avatar.png')
        avatar_file = request.files.get('shop_avatar')

        if avatar_file and avatar_file.filename != '':
            try:
                files = {'shop_avatar': (secure_filename(avatar_file.filename), avatar_file.read(), avatar_file.mimetype)}
                upload_response = requests.post(MAIN_WEB_UPLOAD_AVATAR_API, files=files)
                upload_response.raise_for_status()
                upload_result = upload_response.json()
                if upload_result.get('success'):
                    avatar_filename = upload_result.get('filename')
                    flash(f"✅ Avatar shop '{avatar_filename}' đã được upload thành công!", "success")
                else:
                    flash(f"❗ Lỗi khi upload avatar shop: {upload_result.get('message', 'Không rõ lỗi')}", "error")
            except requests.exceptions.ConnectionError:
                flash('❌ Không thể kết nối đến API upload avatar của web bán hàng!', 'error')
            except requests.exceptions.HTTPError as e:
                flash(f'❌ Lỗi HTTP từ API upload avatar: {e}', 'error')
            except Exception as e:
                flash(f'❌ Lỗi không xác định khi upload avatar: {e}', 'error')
        
        shop_info['shop_avatar'] = avatar_filename

        save_current_admin_shop_info(shop_info)

        updated_shop_data_for_main_web = shop_info.copy()
        updated_shop_data_for_main_web['seller_username'] = session.get('admin_user')
        
        try:
            response = requests.post(MAIN_WEB_UPDATE_SHOP_INFO_API, json=updated_shop_data_for_main_web)
            response.raise_for_status()
            flash('✅ Thông tin web đã được cập nhật và đồng bộ với web bán hàng!', 'success')
            return redirect(url_for('my_shop_info')) # CHUYỂN HƯỚNG TỚI TRANG HIỂN THỊ THÔNG TIN SHOP CỦA ADMIN
        except requests.exceptions.ConnectionError:
            flash('❌ Không thể kết nối đến API cập nhật thông tin shop của web bán hàng!', 'error')
        except requests.exceptions.HTTPError as e:
            flash(f'❌ Lỗi HTTP từ API cập nhật thông tin shop: {e}', 'error')
        except Exception as e:
            flash(f'❌ Lỗi không xác định khi cập nhật thông tin shop: {e}', 'error')

    return render_template('shop_info_form.html', shop_info=shop_info)

# ==== TRANG HIỂN THỊ THÔNG TIN SHOP CỦA ADMIN MỚI ====
@app.route('/my_shop_info')
def my_shop_info():
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để xem thông tin shop của mình!", "warning")
        return redirect(url_for('login_admin'))
    
    shop_info = load_current_admin_shop_info()
    
    # Nếu thông tin chưa được thiết lập, chuyển hướng về form để điền
    if not shop_info.get('info_set', False):
        flash("Vui lòng điền thông tin shop của bạn trước!", "info")
        return redirect(url_for('manage_shop_info'))

    return render_template('my_shop_info.html', shop_info=shop_info, MAIN_WEB_URL=MAIN_WEB_URL)


# ==== ĐĂNG KÝ ADMIN ====
@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if is_admin_logged_in():
        return redirect(url_for('admin_home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_users = load_admin_users()

        if username in admin_users:
            flash("❗ Tài khoản admin đã tồn tại!", "error")
            return redirect(url_for('register_admin'))

        admin_users[username] = {
            "password_hash": generate_password_hash(password),
            "shop_info": { # Thêm shop_info mặc định khi đăng ký admin mới
                "shop_name": f"Shop của {username}",
                "hotline": "",
                "email": "",
                "address": "",
                "facebook_link": "",
                "zalo_link": "",
                "website_link": "",
                "shop_avatar": "default_shop_avatar.png",
                "info_set": False # Mặc định là FALSE khi mới đăng ký
            }
        }
        save_admin_users(admin_users)
        flash("✅ Đăng ký tài khoản admin thành công! Đăng nhập nhé 😎", "success")
        return redirect(url_for('login_admin'))
    return render_template('auth_admin.html', register=True)

# ==== ĐĂNG NHẬP ADMIN ====
@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if is_admin_logged_in():
        return redirect(url_for('admin_home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_users = load_admin_users()

        if username not in admin_users:
            flash("❌ Tài khoản admin không tồn tại.", "error")
            return redirect(url_for('login_admin'))

        admin_data = admin_users[username]
        hashed_password = admin_data.get("password_hash")

        if not hashed_password or not check_password_hash(hashed_password, password):
            flash("❌ Mật khẩu admin không chính xác.", "error")
            return redirect(url_for('login_admin'))

        session['admin_user'] = username
        flash("✅ Đăng nhập admin thành công!", "success")
        return redirect(url_for('admin_home'))

    return render_template('auth_admin.html', register=False)

# Tại app.py của ADMIN_SITE

# ... (giữ nguyên các import và hàm đã có) ...

@app.route('/manage_products')
def manage_products():
    """Trang quản lý sản phẩm của seller."""
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để truy cập trang này!", "warning")
        return redirect(url_for('login_admin'))

    seller_username = session.get('admin_user')
    products = []
    try:
        response = requests.get(f"{MAIN_WEB_URL}/api/get_products/{seller_username}")
        response.raise_for_status()
        products = response.json()
    except Exception as e:
        flash(f'Lỗi khi lấy danh sách sản phẩm: {e}', 'error')

    return render_template('manage_products.html', products=products, MAIN_WEB_URL=MAIN_WEB_URL)


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Trang chỉnh sửa thông tin sản phẩm."""
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để truy cập trang này!", "warning")
        return redirect(url_for('login_admin'))
    
    seller_username = session.get('admin_user')

    if request.method == 'POST':
        # Lấy dữ liệu từ form
        updated_data = {
            "name": request.form['name'],
            "price": request.form['price'],
            "description": request.form['description'],
            "category_slug": request.form['category_slug'],
            "seller_username": seller_username  # Thêm username để xác thực ở API
        }
        
        try:
            response = requests.post(f"{MAIN_WEB_URL}/api/edit_product/{product_id}", json=updated_data)
            response.raise_for_status()
            result = response.json()
            if result.get('success'):
                flash(f"✅ Đã cập nhật sản phẩm '{updated_data['name']}' thành công!", 'success')
            else:
                flash(f"❗ Lỗi: {result.get('message', 'Không rõ lỗi')}", 'error')
        except Exception as e:
            flash(f'Lỗi khi cập nhật sản phẩm: {e}', 'error')
        
        return redirect(url_for('manage_products'))

    # Xử lý cho phương thức GET
    product_data = None
    try:
        # Lấy thông tin sản phẩm để điền vào form
        response = requests.get(f"{MAIN_WEB_URL}/api/get_products/{seller_username}")
        response.raise_for_status()
        products = response.json()
        product_data = next((p for p in products if p['id'] == product_id), None)
    except Exception as e:
        flash(f'Lỗi khi lấy thông tin sản phẩm: {e}', 'error')
    
    if not product_data:
        flash("Không tìm thấy sản phẩm hoặc bạn không có quyền chỉnh sửa.", "error")
        return redirect(url_for('manage_products'))
        
    return render_template('edit_product.html', product=product_data, categories=categories)


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Xử lý yêu cầu xóa sản phẩm."""
    if not is_admin_logged_in():
        flash("Bạn cần đăng nhập để thực hiện chức năng này!", "warning")
        return redirect(url_for('login_admin'))
    
    seller_username = session.get('admin_user')
    
    try:
        response = requests.post(f"{MAIN_WEB_URL}/api/delete_product/{product_id}", json={"seller_username": seller_username})
        response.raise_for_status()
        result = response.json()

        if result.get('success'):
            flash("✅ Đã xóa sản phẩm thành công!", 'success')
        else:
            flash(f"❗ Lỗi khi xóa sản phẩm: {result.get('message')}", 'error')
    except Exception as e:
        flash(f"Lỗi hệ thống khi xóa sản phẩm: {e}", "error")

    return redirect(url_for('manage_products'))

# ==== ĐĂNG XUẤT ADMIN ====
@app.route('/logout_admin')
def logout_admin():
    session.pop('admin_user', None)
    flash("👋 Bạn đã đăng xuất tài khoản admin.", "info")
    return redirect(url_for('login_admin'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)