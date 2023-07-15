from flask import *
from flask_mysqldb import MySQL
from flask_session import Session
from key import *
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from cmail import *
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'Q'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def title():
    return render_template('title.html')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(username,password)
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s AND password = %s', (username, password))
        count = cursor.fetchone()
        print(count) # Get the count value
        cursor.close()
        count=count['COUNT(*)']
        print(count)
        if count:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        name=request.form['name']
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()
        cursor.execute('select count(*) from users where email=%s',[email])
        count1=cursor.fetchone()
        cursor.close()
        if count==1:
            flash('username already in use')
            return render_template('registration.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('registration.html')
        data={'name':name,'username':username,'password':password,'email':email}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data,salt),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('login'))
    return render_template('registration.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        #print(e)
        return 'Link Expired register again'
    else:
        cursor=mysql.connection.cursor()
        username=data['username']
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('login'))
        else:
            cursor.execute('insert into users (USERNAME,name,EMAIL,PASSWORD) values(%s,%s,%s,%s)',[data['name'],data['username'],data['email'],data['password']])
            mysql.connection.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))
        

@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()
        cursor.close()
        count = count['count(*)']
        if count==1:
            cursor=mysql.connection.cursor()
            cursor.execute('SELECT email from users where email=%s',[email])
            status=cursor.fetchone()
            cursor.close()
            subject='Forget Password'
            confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
            body=f"Use this link to reset your password-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Reset link sent check your email')
            return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')


@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mysql.connection.cursor()
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mysql.connection.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('username'):
        session.pop('username')
        flash('User Successfully logged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route('/ask', methods=['GET', 'POST'])
def ask_question():
    if session.get('username'):
        if request.method == 'POST':
            question = request.form['question']
            username = session['username']
            print(username)
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO questions(question, username) VALUES (%s, %s)", (question, username))
            mysql.connection.commit()
            cursor.close()
            flash('Question submitted.')
            return redirect(url_for('home'))
        return render_template('ask.html')

@app.route('/questions')
def questions():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM questions ORDER BY created_at DESC")
    questions = cursor.fetchall()
    cursor.close()
    return render_template('questions.html', questions=questions)


@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
def view_question(question_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = %s", [question_id])
        question = cursor.fetchone()
        if request.method == 'POST':
            answer = request.form['answer']
            username = session['username']
            cursor.execute("INSERT INTO answers(answer, question_id, username) VALUES(%s, %s, %s)", (answer, question_id, username))
            mysql.connection.commit()
            cursor.close()
            flash('Answer submitted.')
            return redirect(url_for('view_question', question_id=question_id))
        cursor.execute("SELECT * FROM answers WHERE question_id = %s ORDER BY created_at ASC", [question_id])
        answers = cursor.fetchall()
        cursor.close()
        return render_template('question.html', question=question, answers=answers)
    return redirect(url_for('login'))
    


@app.route('/reply/<int:answer_id>', methods=['POST'])
def reply(answer_id):
    if session.get('username'):
        if request.method == 'POST':
            reply_text = request.form['reply']
            username = session['username']
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO replies(reply, answer_id, username) VALUES(%s, %s, %s)", (reply_text, answer_id, username))
            mysql.connection.commit()
            cursor.close()
            flash('Reply submitted.')
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT question_id FROM answers WHERE id = %s", [answer_id])
            question_id = cursor.fetchone()['question_id']
            cursor.close()
            return redirect(url_for('view_question', question_id=question_id, answer_id=answer_id))


@app.route('/upvote_answer/<int:answer_id>', methods=['POST'])
def upvote_answer(answer_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE answers SET upvotes = upvotes + 1 WHERE id = %s", [answer_id])
        mysql.connection.commit()
        cursor.close()
        flash('Answer upvoted.')
        # Retrieve the question_id associated with the answer
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT question_id FROM answers WHERE id = %s", [answer_id])
        question_id = cursor.fetchone()['question_id']
        cursor.close()
    return redirect(url_for('view_question', question_id=question_id, answer_id=answer_id))

@app.route('/downvote_answer/<int:answer_id>', methods=['POST'])
def downvote_answer(answer_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE answers SET downvotes = downvotes + 1 WHERE id = %s", [answer_id])
        mysql.connection.commit()
        flash('Answer downvoted.')
        
        # Retrieve the question_id associated with the answer
        cursor.execute("SELECT question_id FROM answers WHERE id = %s", [answer_id])
        question_id = cursor.fetchone()['question_id']
        cursor.close()
        
        return redirect(url_for('view_question', question_id=question_id))

@app.route('/question/<int:question_id>/answer/<int:answer_id>', methods=['GET'])
def view_answer_replies(question_id, answer_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM answers WHERE id = %s", [answer_id])
        answer = cursor.fetchone()
        if not answer:
            flash('Answer not found.')
            return redirect(url_for('view_question', question_id=question_id))
        cursor.execute("SELECT * FROM replies WHERE answer_id = %s ORDER BY created_at ASC", [answer_id])
        replies = cursor.fetchall()
        cursor.close()
        return render_template('answer_replies.html', question_id=question_id, answer_id=answer_id, answer=answer, replies=replies)




@app.route('/upvote_reply/<int:reply_id>/<int:answer_id>', methods=['POST'])
def upvote_reply(reply_id, answer_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE replies SET upvotes = upvotes + 1 WHERE id = %s", [reply_id])
        mysql.connection.commit()
        cursor.execute("SELECT question_id FROM answers WHERE id = %s", [answer_id])
        result = cursor.fetchone()
        if result is not None:
            question_id = result['question_id']  # Extract the value using the 'question_id' key
            cursor.close()
            flash('Reply upvoted.')
            return render_template('answer_replies.html', question_id=question_id, answer_id=answer_id)

        cursor.close()
        flash('Answer not found.')
        return redirect(url_for('view_question'))  # Redirect to an error page or handle accordingly


@app.route('/downvote_reply/<int:reply_id>/<int:answer_id>', methods=['POST'])
def downvote_reply(reply_id, answer_id):
    if session.get('username'):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE replies SET downvotes = downvotes + 1 WHERE id = %s", [reply_id])
        mysql.connection.commit()
        cursor.execute("SELECT question_id FROM answers WHERE id = %s", [answer_id])
        result = cursor.fetchone()
        if result is not None:
            question_id = result['question_id']  # Extract the value using the 'question_id' key
            cursor.close()
            flash('Reply downvoted.')
            return render_template('answer_replies.html', question_id=question_id, answer_id=answer_id)
        
        cursor.close()
        flash('Answer not found.')
        return redirect(url_for('view_question'))  # Redirect to an error page or handle accordingly

if __name__ == '__main__':
    app.run(debug=True)
