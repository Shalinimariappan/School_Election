from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///election.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
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

# Create tables and add initial data
with app.app_context():
    db.create_all()
    
    # Add admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
    
    # Add sample candidates if none exist
    if not Candidate.query.first():
        candidates = [
            Candidate(name="Alice Johnson", symbol="Ladder", position="SPL", code="101"),
            Candidate(name="Bob Smith", symbol="Book", position="SPL", code="102"),
            Candidate(name="Charlie Brown", symbol="Pencil", position="SPL", code="103"),
            Candidate(name="Diana Prince", symbol="Shield", position="ASPL", code="201"),
            Candidate(name="Ethan Hunt", symbol="Star", position="ASPL", code="202"),
            Candidate(name="Fiona Green", symbol="Tree", position="Junior ASPL", code="301"),
            Candidate(name="George Wilson", symbol="Sun", position="Junior ASPL", code="302"),
        ]
        db.session.add_all(candidates)
        db.session.commit()

@app.route('/')
def home():
    return redirect(url_for('election'))

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
    
    candidates = Candidate.query.all()
    positions = {}
    for candidate in candidates:
        if candidate.position not in positions:
            positions[candidate.position] = []
        positions[candidate.position].append(candidate)
    
    return render_template('election.html', positions=positions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('election'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    candidates = Candidate.query.all()
    positions = {}
    total_votes = {}
    
    for candidate in candidates:
        if candidate.position not in positions:
            positions[candidate.position] = []
            total_votes[candidate.position] = 0
        positions[candidate.position].append(candidate)
        total_votes[candidate.position] += candidate.votes
    
    # Create vote charts
    charts = {}
    for position, candidates in positions.items():
        plt.figure()
        names = [c.name for c in candidates]
        votes = [c.votes for c in candidates]
        plt.bar(names, votes)
        plt.title(f'Votes for {position}')
        plt.xlabel('Candidates')
        plt.ylabel('Votes')
        plt.xticks(rotation=45)
        
        img_bytes = BytesIO()
        plt.savefig(img_bytes, format='png', bbox_inches='tight')
        img_bytes.seek(0)
        charts[position] = base64.b64encode(img_bytes.read()).decode('utf-8')
        plt.close()
    
    return render_template('admin.html', positions=positions, charts=charts, total_votes=total_votes)

@app.route('/reset')
def reset():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    # Clear existing data
    db.session.query(Candidate).delete()
    
    # Add sample candidates
    candidates = [
        Candidate(name="Alice Johnson", symbol="Ladder", position="SPL", code="101"),
        Candidate(name="Bob Smith", symbol="Book", position="SPL", code="102"),
        Candidate(name="Charlie Brown", symbol="Pencil", position="SPL", code="103"),
        Candidate(name="Diana Prince", symbol="Shield", position="ASPL", code="201"),
        Candidate(name="Ethan Hunt", symbol="Star", position="ASPL", code="202"),
        Candidate(name="Fiona Green", symbol="Tree", position="Junior ASPL", code="301"),
        Candidate(name="George Wilson", symbol="Sun", position="Junior ASPL", code="302"),
    ]
    
    db.session.add_all(candidates)
    db.session.commit()
    flash('Database reset with sample candidates!', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)