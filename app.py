from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_file
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from fpdf import FPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///election.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ───────────────────────── Models ──────────────────────────
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    has_voted = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    votes = db.Column(db.Integer, default=0)

# ──────────────── Create tables & seed data ────────────────
with app.app_context():
    db.create_all()

    # Ensure admin user exists
    if not User.query.filter_by(username='admin').first():
        db.session.add(
            User(username='admin', password_hash=generate_password_hash('admin123'))
        )

    # Seed candidates if none exist
    if not Candidate.query.first():
        db.session.add_all([
            Candidate(name="Alice Johnson", symbol="Ladder", position="SPL",        code="101"),
            Candidate(name="Bob Smith",      symbol="Book",   position="SPL",        code="102"),
            Candidate(name="Charlie Brown",  symbol="Pencil", position="SPL",        code="103"),
            Candidate(name="Diana Prince",   symbol="Shield", position="ASPL",       code="201"),
            Candidate(name="Ethan Hunt",     symbol="Star",   position="ASPL",       code="202"),
            Candidate(name="Fiona Green",    symbol="Tree",   position="Junior ASPL",code="301"),
            Candidate(name="George Wilson",  symbol="Sun",    position="Junior ASPL",code="302"),
        ])
    db.session.commit()

# ───────────────────────── Routes ──────────────────────────
@app.route('/')
def home():
    return redirect(url_for('election'))

# ---------- Voting page ----------
@app.route('/election', methods=['GET', 'POST'])
def election():
    if request.method == 'POST':
        code = request.form.get('code')

        candidate = Candidate.query.filter_by(code=code).first()
        if candidate:
            candidate.votes += 1
            db.session.commit()
            flash(f'Voted for {candidate.name} ({candidate.symbol})!', 'success')
        else:
            flash('Invalid code. Please try again.', 'danger')
        return redirect(url_for('election'))

    # Group candidates by position
    positions = {}
    for c in Candidate.query.all():
        positions.setdefault(c.position, []).append(c)
    return render_template('election.html', positions=positions)

# ---------- Auth ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('election'))

# ---------- Admin dashboard ----------
@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    candidates = Candidate.query.all()

    # Group and tally
    positions, total_votes = {}, {}
    for c in candidates:
        positions.setdefault(c.position, []).append(c)
        total_votes[c.position] = total_votes.get(c.position, 0) + c.votes

    # Build bar-chart images
    charts = {}
    for position, cands in positions.items():
        plt.figure()
        plt.bar([c.name for c in cands], [c.votes for c in cands])
        plt.title(f'Votes for {position}')
        plt.xticks(rotation=45)
        plt.ylabel('Votes')

        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        charts[position] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    return render_template(
        'admin.html',
        positions=positions,
        charts=charts,
        total_votes=total_votes
    )

# ---------- NEW: Reset all votes ----------
@app.route('/reset_votes')
def reset_votes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    # Clear candidate vote counts
    for c in Candidate.query.all():
        c.votes = 0

    # Allow users to vote again
    for u in User.query.all():
        u.has_voted = False

    db.session.commit()
    flash('All votes have been reset. Everyone can vote again!', 'success')
    return redirect(url_for('admin'))

# ---------- PDF Download ----------
@app.route('/download')
def download():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', size=16)
    pdf.cell(0, 10, 'School Election Results', ln=1)

    # Group candidates by position
    grouped = {}
    for c in Candidate.query.all():
        grouped.setdefault(c.position, []).append(c)

    pdf.set_font('Helvetica', size=12)
    for position in sorted(grouped):
        pdf.set_font('Helvetica', size=14)
        pdf.cell(0, 8, f'\n{position}', ln=1)
        pdf.set_font('Helvetica', size=12)
        for cand in grouped[position]:
            pdf.cell(
                0, 6,
                f'{cand.name} – {cand.votes} votes',
                ln=1
            )
        pdf.ln(1)

    tmp = '/tmp/election_results.pdf'
    pdf.output(tmp)
    return send_file(tmp, as_attachment=True)

# ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
