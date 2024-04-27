import psycopg2
from flask import Flask, render_template, request, redirect, url_for

conn = psycopg2.connect(user="postgres",
                        password="12341234",
                        host="127.0.0.1",
                        port="5432",
                        dbname='tasks_db')

app = Flask(__name__)


@app.route("/")
def index():
    # Получение данных из базы данных
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM your_table")
    data = cursor.fetchall()
    cursor.close()
    return render_template("index.html", data=data)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if request.method == "POST":
        # Обновление данных в базе данных
        cursor = conn.cursor()
        cursor.execute("UPDATE your_table SET ... WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        return redirect(url_for("index"))
    else:
        # Получение данных из базы данных для редактирования
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM your_table WHERE id = %s", (id,))
        data = cursor.fetchone()
        cursor.close()
        return render_template("edit.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
