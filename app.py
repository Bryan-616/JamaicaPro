# app.py (código completo con ventas)
from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)
DB_NAME = 'jamaica.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                cantidad INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                cantidad INTEGER,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/productos')
def productos():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
    return render_template('productos.html', productos=productos)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        tipo = request.form['tipo']
        cantidad = request.form['cantidad']
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO productos (nombre, tipo, cantidad) VALUES (?, ?, ?)",
                           (nombre, tipo, cantidad))
            conn.commit()
        return redirect('/productos')
    return render_template('agregar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            nombre = request.form['nombre']
            tipo = request.form['tipo']
            cantidad = request.form['cantidad']
            cursor.execute("UPDATE productos SET nombre=?, tipo=?, cantidad=? WHERE id=?",
                           (nombre, tipo, cantidad, id))
            conn.commit()
            return redirect('/productos')
        else:
            cursor.execute("SELECT * FROM productos WHERE id=?", (id,))
            producto = cursor.fetchone()
            return render_template('editar.html', producto=producto)

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id=?", (id,))
        conn.commit()
    return redirect('/productos')

@app.route('/ventas')
def ventas():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT v.id, p.nombre, v.cantidad, v.fecha
                          FROM ventas v
                          JOIN productos p ON v.producto_id = p.id
                          ORDER BY v.fecha DESC''')
        ventas = cursor.fetchall()
    return render_template('ventas.html', ventas=ventas)

@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM productos")
        productos = cursor.fetchall()
    if request.method == 'POST':
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ventas (producto_id, cantidad) VALUES (?, ?)",
                           (producto_id, cantidad))
            cursor.execute("UPDATE productos SET cantidad = cantidad - ? WHERE id = ?",
                           (cantidad, producto_id))
            conn.commit()
        return redirect('/ventas')
    return render_template('registrar_venta.html', productos=productos)

@app.route('/estadisticas')
def estadisticas():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Productos más vendidos
        cursor.execute('''
            SELECT p.nombre, SUM(v.cantidad) as total
            FROM ventas v
            JOIN productos p ON v.producto_id = p.id
            GROUP BY v.producto_id
        ''')
        datos_ventas = cursor.fetchall()

        nombres = [x[0] for x in datos_ventas]
        cantidades = [x[1] for x in datos_ventas]

        # Stock actual
        cursor.execute('SELECT nombre, cantidad FROM productos')
        stock = cursor.fetchall()
        stock_nombres = [x[0] for x in stock]
        stock_cantidades = [x[1] for x in stock]

    return render_template("estadisticas.html",
                           nombres=nombres,
                           cantidades=cantidades,
                           stock_nombres=stock_nombres,
                           stock_cantidades=stock_cantidades)

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import io

@app.route('/reporte_pdf')
def reporte_pdf():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 50, "Reporte General - JamaicaPro")

    y = height - 100
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Inventario Actual:")
    y -= 20

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Inventario
        pdf.setFont("Helvetica", 10)
        cursor.execute("SELECT nombre, tipo, cantidad FROM productos")
        for nombre, tipo, cantidad in cursor.fetchall():
            pdf.drawString(60, y, f"{nombre} ({tipo}): {cantidad} unidades")
            y -= 15
            if y < 100:
                pdf.showPage()
                y = height - 50

        # Ventas
        y -= 20
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Ventas Registradas:")
        y -= 20

        pdf.setFont("Helvetica", 10)
        cursor.execute('''
            SELECT p.nombre, v.cantidad, v.fecha
            FROM ventas v
            JOIN productos p ON v.producto_id = p.id
            ORDER BY v.fecha DESC
        ''')
        for nombre, cantidad, fecha in cursor.fetchall():
            pdf.drawString(60, y, f"{fecha[:10]} - {nombre}: {cantidad} unidades")
            y -= 15
            if y < 100:
                pdf.showPage()
                y = height - 50

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="reporte_jamaica.pdf", mimetype='application/pdf')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)