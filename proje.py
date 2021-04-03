from flask  import Flask,render_template, request, redirect, logging, session, flash, url_for
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import email_validator
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL 
import sqlite3
from functools import wraps

 
 
 # Kullanici Giris Decorator



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Yetkiniz yok lütfen giriş yapın", "danger")
            return redirect(url_for("login"))
    return decorated_function



# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators = [validators.Length(min=3,max=27)])
    username = StringField("Kullanıcı Adı", validators = [validators.Length(min=5,max=20)])
    email = StringField("Email Adresi", validators = [validators.Email(message="Lütfen geçerli bir email adresi girin")])
    password = PasswordField("Parolanızı Girin", validators = [validators.DataRequired(message = "Lütfen bir parola belirleyin"), validators.EqualTo(fieldname = "confirm", message = "Uyuşmayan parola")])
    confirm = PasswordField("Parola Doğrula")



class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")



app  = Flask(__name__)
app.secret_key = "ybblog"


# Windows kullanicisi iseniz "localhost" olarak ayarlayabilirsiniz.
app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


# Ana sayfa
@app.route("/")
def index():
    return render_template("index.html")


# Hakkimda yazisi
@app.route("/about")
def about():
    return render_template("about.html")



# Makale Sayfasi
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles"
    result = cursor.execute(sorgu)
    if result > 0 :
        articles = cursor.fetchall()
        return render_template("articles.html", articles =  articles)
    else:
        return render_template("articles.html")



## Dashboard Ekrani
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],) )
    
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)

    else:
        return render_template("dashboard.html")




# register - kayit olma
@app.route("/register", methods = ["GET","POST"] )
def register():
    form = RegisterForm(request.form)

    if request.method  == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name, email, username, password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()            
        cursor.close()

        flash(message="Başarıyla kayıt oldunuz.", category="success")
        

        return redirect(url_for("login"))

    else:
        return render_template("register.html",  form = form)


### login islemi
@app.route("/login" , methods = ["GET", "POST"] )
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        entered_password = form.password.data
        
        cursor = mysql.connection.cursor()
        sorgu  = "Select * from users where username = %s"

        result = cursor.execute(sorgu , (username,))
        if result >0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(entered_password, real_password):
                flash(message="Başarıyla giriş yaptınız.",category="success")
                
                session["logged_in"] = True
                session["username"] = username

                
                return redirect(url_for("index"))
                


                
            else:
                flash(message="Parolanızı yanlış girdiniz.",category="danger")
                return redirect(url_for("login")) 


        else:
            flash(message="Böyle bir kullanıcı yoktur.", category="danger")
            return redirect(url_for("login"))

    return render_template("login.html", form = form)


## Detay Sayfasi
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu, (id, ) )

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")




#Logout islemi

@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))


# Makale Ekleme
@app.route("/adarticle", methods= ["GET","POST"])
def adarticle():
    form  = ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title = form.title.data
        content = form.content.data


        cursor = mysql.connection.cursor()
        
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        
        cursor.execute(sorgu, (title, session["username"],content))
        
        mysql.connection.commit()
        
        cursor.close()
        
        flash(message="Makale başarıyla eklendi.", category="success")


        return render_template("dashboard.html")

    return render_template("adarticle.html", form = form)




# Makale Silme
@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * From articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))


    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))

    else:
        flash("Böyle bir makale yok veya sizin bunu silme yetkiniz yok.", "danger")
        return redirect(url_for("index"))



# Makale Guncelleme
@app.route("/edit/<string:id>", methods= ["GET", "POST"])
@login_required
def update(id):
    if request.method =="GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok", "danger")
            return redirect(url_for("index"))                        
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
            
    else:
        # POST 
        form  = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        

        sorgu2 = "Update articles Set title = %s,content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent, id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi", "success")
        return redirect(url_for("dashboard"))





# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators= [validators.Length(min = 5 , max = 100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.Length(min=10)])



## URL Arama
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        
        sorgu = "select * from articles where title like '%"+ keyword + "%'  "
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı.", "warning")
            return redirect(url_for("articles"))

        else:
            articles = cursor.fetchall()

            return render_template("articles.html", articles = articles )

            
         


if __name__=="__main__":
    app.run(debug=True)

