from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import main as sra
from itertools import combinations
from functools import wraps
from secrets import token_urlsafe
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
import os

app.secret_key = os.environ.get("SRA_SECRET_KEY", "sra-local-development-key-change-me")


def init_auth():
    c = db()
    cur = c.cursor()

    try:
        # --------------------------------------------------------
        # COMPANY TABLE
        # --------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                company_id SERIAL PRIMARY KEY,
                company_name VARCHAR(150) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing data belongs to this company
        cur.execute("""
            INSERT INTO companies (company_name)
            VALUES ('Existing Company')
            ON CONFLICT (company_name) DO NOTHING
        """)

        cur.execute("""
            SELECT company_id
            FROM companies
            WHERE company_name = 'Existing Company'
        """)
        existing_company_id = cur.fetchone()[0]

        # --------------------------------------------------------
        # USER TABLE
        # --------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sra_users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user'
                    CHECK (role IN ('admin','user')),
                company_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # For an already-existing sra_users table
        cur.execute("""
            ALTER TABLE sra_users
            ADD COLUMN IF NOT EXISTS company_id INT
        """)

        # Assign old users to the existing company
        cur.execute("""
            UPDATE sra_users
            SET company_id = %s
            WHERE company_id IS NULL
        """, (existing_company_id,))

        # Add foreign-key relationship
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_sra_users_company'
                ) THEN
                    ALTER TABLE sra_users
                    ADD CONSTRAINT fk_sra_users_company
                    FOREIGN KEY (company_id)
                    REFERENCES companies(company_id)
                    ON DELETE CASCADE;
                END IF;
            END
            $$;
        """)

        # --------------------------------------------------------
        # INITIAL ADMIN ACCOUNT
        # --------------------------------------------------------
        admin_user = os.environ.get(
            "SRA_ADMIN_USERNAME", "admin"
        ).strip() or "admin"

        admin_pass = os.environ.get(
            "SRA_ADMIN_PASSWORD", "admin123"
        )

        cur.execute(
            "SELECT user_id FROM sra_users WHERE username=%s",
            (admin_user,)
        )

        if not cur.fetchone():
            cur.execute("""
                INSERT INTO sra_users
                (username, password_hash, role, company_id)
                VALUES (%s, %s, 'admin', %s)
            """, (
                admin_user,
                generate_password_hash(admin_pass),
                existing_company_id
            ))

            print(f"Created initial admin account: {admin_user}")

            if "SRA_ADMIN_PASSWORD" not in os.environ:
                print(
                    "WARNING: Using demo admin password 'admin123'. "
                    "Set SRA_ADMIN_PASSWORD before deployment."
                )

        # Make sure admin belongs to Existing Company
        cur.execute("""
            UPDATE sra_users
            SET company_id = %s
            WHERE username = %s
              AND company_id IS NULL
        """, (existing_company_id, admin_user))

        c.commit()

    except Exception:
        c.rollback()
        raise

    finally:
        cur.close()
        c.close()

def current_user():
    uid = session.get('user_id')

    if not uid:
        return None

    row = fetchone("""
        SELECT user_id, username, role, company_id
        FROM sra_users
        WHERE user_id=%s
    """, (uid,))

    if not row:
        session.clear()
        return None

    return {
        'id': row[0],
        'username': row[1],
        'role': row[2],
        'company_id': row[3]
    }
def current_company_id():
    user = current_user()

    if not user:
        return None

    return user['company_id']
def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user: return redirect(url_for('login', next=request.path))
        if user['role'] != 'admin':
            flash('Administrator access is required for this action.', 'error')
            return redirect(url_for('dashboard'))
        return fn(*args, **kwargs)
    return wrapped

def csrf_token():
    if 'csrf_token' not in session: session['csrf_token'] = token_urlsafe(32)
    return session['csrf_token']

@app.context_processor
def inject_auth():
    return {'current_user': current_user(), 'csrf_token': csrf_token()}

@app.before_request
def security_gate():
    if request.endpoint in ('login', 'static'):
        return
    if not current_user():
        return redirect(url_for('login', next=request.full_path))
    if request.method == 'POST':
        token = request.form.get('_csrf')
        if not token or token != session.get('csrf_token'):
            return render_template('error.html', error='Security check failed. Refresh the page and try again.'), 400

def db(): return sra.get_connection()

def fetchall(q,p=()):
    c=db(); cur=c.cursor()
    try: cur.execute(q,p); return cur.fetchall()
    finally: cur.close(); c.close()

def fetchone(q,p=()):
    c=db(); cur=c.cursor()
    try: cur.execute(q,p); return cur.fetchone()
    finally: cur.close(); c.close()

def repair_employee_capacity():
    """Reconcile stored employee workload/availability for the current company."""
    company_id = current_company_id()
    c = db(); cur = c.cursor()
    try:
        cur.execute("""
            UPDATE employees e
            SET workload = LEAST(100, GREATEST(0, COALESCE((
                    SELECT SUM(a.allocation_percentage)
                    FROM allocations a
                    WHERE a.employee_id=e.employee_id
                      AND a.company_id=e.company_id
                ), 0))),
                availability = 100 - LEAST(100, GREATEST(0, COALESCE((
                    SELECT SUM(a.allocation_percentage)
                    FROM allocations a
                    WHERE a.employee_id=e.employee_id
                      AND a.company_id=e.company_id
                ), 0)))
            WHERE e.company_id = %s
        """, (company_id,))
        changed = cur.rowcount
        c.commit()
        return changed
    except Exception:
        c.rollback(); raise
    finally:
        cur.close(); c.close()


def log_company_allocation_history(c, employee_id, project_id, action, old_allocation, new_allocation):
    c.cursor().execute(
        """INSERT INTO allocation_history
           (employee_id,project_id,action,old_allocation,new_allocation,company_id)
           VALUES(%s,%s,%s,%s,%s,%s)""",
        (employee_id,project_id,action,old_allocation,new_allocation,current_company_id())
    )


def company_employee(eid):
    return fetchone(
        "SELECT employee_id,name,experience,availability,workload FROM employees WHERE employee_id=%s AND company_id=%s",
        (eid, current_company_id())
    )


def company_project(pid):
    return fetchone(
        "SELECT project_id,name,priority,required_allocation FROM projects WHERE project_id=%s AND company_id=%s",
        (pid, current_company_id())
    )


def company_skill(sid):
    return fetchone(
        "SELECT skill_id,skill_name FROM skills WHERE skill_id=%s AND company_id=%s",
        (sid, current_company_id())
    )


def company_project_skills(pid):
    return [
        r[0] for r in fetchall("""
            SELECT s.skill_name
            FROM project_skills ps
            JOIN skills s ON s.skill_id=ps.skill_id
            WHERE ps.project_id=%s
              AND ps.company_id=%s
              AND s.company_id=%s
            ORDER BY s.skill_name
        """, (pid, current_company_id(), current_company_id()))
    ]


def company_employee_skills(eid):
    return [
        r[0] for r in fetchall("""
            SELECT s.skill_name
            FROM employee_skills es
            JOIN skills s ON s.skill_id=es.skill_id
            WHERE es.employee_id=%s
              AND es.company_id=%s
              AND s.company_id=%s
            ORDER BY s.skill_name
        """, (eid, current_company_id(), current_company_id()))
    ]

def sync_employee(cur, employee_id):
    """Make employee workload/capacity exactly match this company's allocation rows."""
    company_id = current_company_id()
    cur.execute("""
        SELECT COALESCE(SUM(allocation_percentage),0)
        FROM allocations
        WHERE employee_id=%s AND company_id=%s
    """, (employee_id, company_id))
    workload = min(100.0, max(0.0, float(cur.fetchone()[0] or 0)))
    cur.execute("""
        UPDATE employees
        SET workload=%s, availability=%s
        WHERE employee_id=%s AND company_id=%s
    """, (workload, 100.0-workload, employee_id, company_id))
    return workload

def employee_rows():

    company_id = current_company_id()

    return fetchall("""
        SELECT
            e.employee_id,
            e.name,
            e.experience,
            (100 - e.workload) AS availability,
            e.workload,
            COALESCE(
                STRING_AGG(
                    s.skill_name,
                    ', ' ORDER BY s.skill_name
                ),
                'No skills'
            )
        FROM employees e

        LEFT JOIN employee_skills es
            ON e.employee_id = es.employee_id
            AND es.company_id = e.company_id

        LEFT JOIN skills s
            ON es.skill_id = s.skill_id
            AND s.company_id = e.company_id

        WHERE e.company_id = %s

        GROUP BY
            e.employee_id,
            e.name,
            e.experience,
            e.workload

        ORDER BY e.employee_id
    """, (company_id,))

def project_rows():
    company_id = current_company_id()
    return fetchall("""
        SELECT p.project_id,p.name,p.priority,p.required_allocation,
               COALESCE(SUM(a.allocation_percentage),0)
        FROM projects p
        LEFT JOIN allocations a
          ON p.project_id=a.project_id
         AND a.company_id=p.company_id
        WHERE p.company_id=%s
        GROUP BY p.project_id,p.name,p.priority,p.required_allocation
        ORDER BY p.project_id
    """, (company_id,))

def dashboard_data():
    company_id = current_company_id()
    employees=fetchone("SELECT COUNT(*) FROM employees WHERE company_id=%s", (company_id,))[0]
    projects=fetchone("SELECT COUNT(*) FROM projects WHERE company_id=%s", (company_id,))[0]
    allocations=fetchone("SELECT COUNT(*) FROM allocations WHERE company_id=%s", (company_id,))[0]
    avg_load,max_load,underutilized,overloaded=fetchone("""
        SELECT COALESCE(AVG(workload),0),COALESCE(MAX(workload),0),
               COUNT(*) FILTER(WHERE workload<50),
               COUNT(*) FILTER(WHERE workload>90)
        FROM employees
        WHERE company_id=%s
    """, (company_id,))
    cards=[]; scores=[]; alerts=[]
    for pid,name,priority,required,current in project_rows():
        required=float(required or 0); current=float(current or 0); gap=max(required-current,0); score=100 if required<=0 else min(current/required*100,100)
        scores.append(score); cards.append({'id':pid,'name':name,'priority':priority,'required':required,'current':current,'gap':gap,'score':score})
        if gap: alerts.append({'id':pid,'name':name,'priority':priority,'gap':gap})
    staffing=sum(scores)/len(scores) if scores else 100
    balance=max(0,100-(float(overloaded)/employees*100 if employees else 0)-(float(underutilized)/employees*50 if employees else 0))
    health=staffing*.6+balance*.4
    status='EXCELLENT' if health>=80 else 'GOOD' if health>=60 else 'NEEDS ATTENTION' if health>=40 else 'CRITICAL'
    rank={'Critical':4,'High':3,'Medium':2,'Low':1}; alerts.sort(key=lambda x:(rank.get(str(x['priority']).title(),1),x['gap']),reverse=True)
    history=fetchone("""
        SELECT COUNT(*),
               COUNT(*) FILTER(WHERE UPPER(action)='ADD'),
               COUNT(*) FILTER(WHERE UPPER(action)='MODIFY'),
               COUNT(*) FILTER(WHERE UPPER(action)='REMOVE')
        FROM allocation_history
        WHERE company_id=%s
    """, (company_id,))
    return dict(employees=employees,projects=projects,allocations=allocations,avg_load=float(avg_load or 0),max_load=float(max_load or 0),underutilized=underutilized,overloaded=overloaded,staffing=staffing,balance=balance,health=health,status=status,projects_data=cards,alerts=alerts,history=history)

def recommendation_data(pid):
    p = company_project(pid)
    if not p:
        raise ValueError('Project not found in your company.')

    req = company_project_skills(pid)
    out = []

    employees = fetchall("""
        SELECT employee_id,name,experience,
               (100-workload) AS availability,workload
        FROM employees
        WHERE company_id=%s
        ORDER BY employee_id
    """, (current_company_id(),))

    for eid,name,exp,av,load in employees:
        skills = company_employee_skills(eid)
        sm = float(sra.calculate_skill_match(skills, req))
        score = float(sra.calculate_match_score(sm, av, load, exp))
        out.append(dict(
            id=eid,
            name=name,
            experience=float(exp or 0),
            availability=float(av or 0),
            workload=float(load or 0),
            skill_match=round(sm,2),
            score=round(score,2),
            skills=skills,
            matched_skills=sorted(set(skills)&set(req)),
            missing_skills=sorted(set(req)-set(skills))
        ))
    out.sort(key=lambda x:x['score'],reverse=True)
    for i,x in enumerate(out,1): x['rank']=i; x['recommendation']='EXCELLENT' if x['score']>=60 and x['skill_match']>=75 else 'GOOD' if x['score']>=45 and x['skill_match']>=50 else 'LIMITED' if x['skill_match']>0 else 'LOW'
    return p,req,out

def team_data(pid):
    p,req,recs=recommendation_data(pid); candidates=[x for x in recs if x['availability']>0 and x['workload']<100]
    best=None
    # Small portfolio: exhaustive combinations gives a transparent optimal team.
    for r in range(1,min(4,len(candidates))+1):
        for combo in combinations(candidates,r):
            skills=set().union(*(set(x['skills']) for x in combo)); coverage=100*len(skills&set(req))/len(req) if req else 100
            capacity=sum(min(x['availability'],100-x['workload']) for x in combo); score=sum(x['score'] for x in combo)/r
            key=(coverage, min(capacity,100), score, -r)
            if best is None or key>best[0]: best=(key,combo,skills)
        if best and best[0][0]>=100: break
    if not best: return p,req,[],0
    return p,req,list(best[1]),best[0][0]

def feature_page(title,subtitle,kind,data=None): return render_template('feature.html',title=title,subtitle=subtitle,kind=kind,data=data or {})

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        row = fetchone("""
            SELECT user_id, username, password_hash, role, company_id
            FROM sra_users
            WHERE username=%s
        """, (username,))

        if row and check_password_hash(row[2], password):

            # Every authenticated session remembers its company
            session.clear()
            session['user_id'] = row[0]
            session['company_id'] = row[4]
            session['csrf_token'] = token_urlsafe(32)

            nxt = (
                request.args.get('next')
                or request.form.get('next')
                or url_for('dashboard')
            )

            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = url_for('dashboard')

            return redirect(nxt)

        flash('Invalid username or password.', 'error')

    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear(); flash('You have been logged out.', 'success'); return redirect(url_for('login'))

@app.route('/users', methods=['GET', 'POST'])
@admin_required
def users():

    if request.method == 'POST':

        company_name = request.form.get('company_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        c = None
        cur = None

        try:
            if len(company_name) < 2:
                raise ValueError(
                    'Company name must contain at least 2 characters.'
                )

            if len(username) < 3:
                raise ValueError(
                    'Username must contain at least 3 characters.'
                )

            if len(password) < 8:
                raise ValueError(
                    'Password must contain at least 8 characters.'
                )

            if role not in ('admin', 'user'):
                raise ValueError('Invalid role.')

            c = db()
            cur = c.cursor()

            # Check whether username already exists
            cur.execute("""
                SELECT user_id
                FROM sra_users
                WHERE username = %s
            """, (username,))

            if cur.fetchone():
                raise ValueError(
                    f'Username {username} already exists.'
                )

            # Check whether company already exists
            cur.execute("""
                SELECT company_id
                FROM companies
                WHERE LOWER(company_name) = LOWER(%s)
            """, (company_name,))

            company = cur.fetchone()

            if company:
                company_id = company[0]
                raise ValueError(
                    f'Company "{company_name}" already exists. '
                    'Please use a different company name.'
                )

            # Create a NEW company/workspace
            cur.execute("""
                INSERT INTO companies (company_name)
                VALUES (%s)
                RETURNING company_id
            """, (company_name,))

            company_id = cur.fetchone()[0]

            # Create the user inside that company/workspace
            cur.execute("""
                INSERT INTO sra_users
                (username, password_hash, role, company_id)
                VALUES (%s, %s, %s, %s)
            """, (
                username,
                generate_password_hash(password),
                role,
                company_id
            ))

            c.commit()

            flash(
                f'User {username} created successfully for '
                f'{company_name}.',
                'success'
            )

        except Exception as e:

            if c:
                try:
                    c.rollback()
                except Exception:
                    pass

            flash(str(e), 'error')

        finally:

            if cur:
                try:
                    cur.close()
                except Exception:
                    pass

            if c:
                try:
                    c.close()
                except Exception:
                    pass

    # Show users belonging to the currently logged-in admin's company
    rows = fetchall("""
        SELECT
            u.user_id,
            c.company_name,
            u.username,
            u.role,
            u.created_at
        FROM sra_users u
        JOIN companies c
            ON u.company_id = c.company_id
        WHERE u.company_id = %s
        ORDER BY u.user_id
    """, (current_company_id(),))

    return render_template('users.html', users=rows)


@app.route('/')
def dashboard(): return render_template('dashboard.html',**dashboard_data())

@app.route('/employees', methods=['GET', 'POST'])
def employees():

    if request.method == 'POST':

        if (u := current_user())['role'] != 'admin':
            flash(
                'Administrator access is required to add employees.',
                'error'
            )
            return redirect(url_for('employees'))

        try:
            name = request.form['name'].strip()
            exp = float(request.form['experience'])
            load = float(request.form['workload'])

            if not name or exp < 0 or not 0 <= load <= 100:
                raise ValueError(
                    'Check employee values. Name required, '
                    'experience >=0 and workload must be 0-100%.'
                )

            av = 100.0 - load
            company_id = current_company_id()

            c = db()
            cur = c.cursor()

            cur.execute("""
                INSERT INTO employees
                (name, experience, availability, workload, company_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING employee_id
            """, (
                name,
                exp,
                av,
                load,
                company_id
            ))

            eid = cur.fetchone()[0]

            c.commit()
            cur.close()
            c.close()

            flash(
                f'Employee {name} added (ID {eid}).',
                'success'
            )

        except Exception as e:
            try:
                c.rollback()
                cur.close()
                c.close()
            except Exception:
                pass

            flash(str(e), 'error')

    return render_template(
        'employees.html',
        employees=employee_rows()
    )

@app.route('/skills', methods=['GET', 'POST'])
def skills():

    if request.method == 'POST':

        if (u := current_user())['role'] != 'admin':
            flash(
                'Administrator access is required to add skills.',
                'error'
            )
            return redirect(url_for('skills'))

        c = None
        cur = None

        try:
            name = request.form['skill_name'].strip()

            if not name:
                raise ValueError('Skill name cannot be empty.')

            company_id = current_company_id()

            c = db()
            cur = c.cursor()

            # Check whether this skill already exists
            # ONLY inside the current company
            cur.execute("""
                SELECT skill_id
                FROM skills
                WHERE LOWER(skill_name) = LOWER(%s)
                  AND company_id = %s
            """, (name, company_id))

            if cur.fetchone():
                raise ValueError(
                    'Skill already exists in your company.'
                )

            # Add skill to current company's workspace
            cur.execute("""
                INSERT INTO skills
                (skill_name, company_id)
                VALUES (%s, %s)
                RETURNING skill_id
            """, (
                name,
                company_id
            ))

            sid = cur.fetchone()[0]

            c.commit()

            flash(
                f'Skill added (ID {sid}).',
                'success'
            )

        except Exception as e:

            if c:
                try:
                    c.rollback()
                except Exception:
                    pass

            flash(str(e), 'error')

        finally:

            if cur:
                try:
                    cur.close()
                except Exception:
                    pass

            if c:
                try:
                    c.close()
                except Exception:
                    pass

    # Show ONLY skills belonging to the logged-in
    # user's company
    skills_list = fetchall("""
        SELECT
            skill_id,
            skill_name
        FROM skills
        WHERE company_id = %s
        ORDER BY skill_id
    """, (current_company_id(),))

    return render_template(
        'skills.html',
        skills=skills_list
    )

@app.route('/projects', methods=['GET','POST'])
def projects():
    if request.method == 'POST':
        if (u := current_user())['role'] != 'admin':
            flash('Administrator access is required to add projects.','error')
            return redirect(url_for('projects'))

        c = cur = None
        try:
            name = request.form['name'].strip()
            priority = request.form['priority'].capitalize()
            req = float(request.form['required_allocation'])

            if not name or priority not in ('High','Medium','Low') or not 0 < req <= 100:
                raise ValueError('Enter a name, High/Medium/Low priority and allocation 1-100%.')

            c = db(); cur = c.cursor()
            cur.execute("""
                INSERT INTO projects
                (name,priority,required_allocation,company_id)
                VALUES(%s,%s,%s,%s)
                RETURNING project_id
            """, (name,priority,req,current_company_id()))
            pid = cur.fetchone()[0]
            c.commit()
            flash(f'Project added (ID {pid}).','success')
        except Exception as e:
            if c:
                c.rollback()
            flash(str(e),'error')
        finally:
            if cur: cur.close()
            if c: c.close()

    rows = project_rows()
    company_id = current_company_id()
    sk = {
        r[0]: [x[0] for x in fetchall("""
            SELECT s.skill_name
            FROM project_skills ps
            JOIN skills s ON s.skill_id=ps.skill_id
            WHERE ps.project_id=%s
              AND ps.company_id=%s
              AND s.company_id=%s
            ORDER BY s.skill_name
        """, (r[0],company_id,company_id))]
        for r in rows
    }
    return render_template('projects.html',projects=rows,skills=sk)

@app.route('/skills/assign', methods=['GET','POST'])
def assign_skills():
    company_id = current_company_id()

    if request.method == 'POST':
        if (u := current_user())['role'] != 'admin':
            flash('Administrator access is required to assign skills.','error')
            return redirect(url_for('assign_skills'))

        target = request.form['target']
        owner = int(request.form['owner_id'])
        sid = int(request.form['skill_id'])

        if target not in ('employee','project'):
            flash('Invalid skill assignment target.','error')
            return redirect(url_for('assign_skills'))

        table = 'employee_skills' if target == 'employee' else 'project_skills'
        col = 'employee_id' if target == 'employee' else 'project_id'

        c = cur = None
        try:
            owner_exists = fetchone(
                f'SELECT 1 FROM {"employees" if target == "employee" else "projects"} WHERE {col}=%s AND company_id=%s',
                (owner, company_id)
            )
            if not owner_exists:
                raise ValueError('Selected employee/project does not belong to your company.')

            if not company_skill(sid):
                raise ValueError('Selected skill does not belong to your company.')

            if fetchone(
                f'SELECT 1 FROM {table} WHERE {col}=%s AND skill_id=%s AND company_id=%s',
                (owner,sid,company_id)
            ):
                raise ValueError('That skill is already assigned.')

            c = db(); cur = c.cursor()
            cur.execute(
                f'INSERT INTO {table}({col},skill_id,company_id) VALUES(%s,%s,%s)',
                (owner,sid,company_id)
            )
            c.commit()
            flash('Skill assigned successfully.','success')
        except Exception as e:
            if c:
                c.rollback()
            flash(str(e),'error')
        finally:
            if cur: cur.close()
            if c: c.close()

    return render_template(
        'assign_skills.html',
        employees=fetchall('SELECT employee_id,name FROM employees WHERE company_id=%s ORDER BY employee_id',(company_id,)),
        projects=fetchall('SELECT project_id,name FROM projects WHERE company_id=%s ORDER BY project_id',(company_id,)),
        skills=fetchall('SELECT skill_id,skill_name FROM skills WHERE company_id=%s ORDER BY skill_id',(company_id,))
    )

@app.route('/match')
def match():
    company_id = current_company_id()
    ps = fetchall('SELECT project_id,name FROM projects WHERE company_id=%s ORDER BY project_id',(company_id,))
    employees = fetchall('SELECT employee_id,name FROM employees WHERE company_id=%s ORDER BY employee_id',(company_id,))
    pid=request.args.get('project_id',type=int)
    eid=request.args.get('employee_id',type=int)
    result=None
    error=None

    if pid and eid:
        try:
            p = company_project(pid)
            e = company_employee(eid)
            if not p or not e:
                raise ValueError('Employee or project not found in your company.')
            req = company_project_skills(pid)
            skills = company_employee_skills(eid)
            sm=float(sra.calculate_skill_match(skills,req))
            score=float(sra.calculate_match_score(sm,e[3],e[4],e[2]))
            result=dict(
                project=p, employee=e, required=req, skills=skills,
                matched=sorted(set(req)&set(skills)),
                missing=sorted(set(req)-set(skills)),
                skill_match=sm, score=score
            )
        except Exception as ex:
            error=str(ex)

    return render_template(
        'match.html',projects=ps,employees=employees,
        pid=pid,eid=eid,result=result,error=error
    )

@app.route('/recommendations')
def recommendations():
    ps=fetchall('SELECT project_id,name,priority,required_allocation FROM projects WHERE company_id=%s ORDER BY project_id',(current_company_id(),))
    pid=request.args.get('project_id',type=int); project=None;req=[];results=[];error=None
    if pid:
        try: project,req,results=recommendation_data(pid)
        except Exception as e:error=str(e)
    return render_template('recommendations.html',projects=ps,selected_project=pid,project=project,required_skills=req,recommendations=results,error=error)

@app.route('/team')
def team():
    ps=fetchall('SELECT project_id,name,priority,required_allocation FROM projects WHERE company_id=%s ORDER BY project_id',(current_company_id(),))
    pid=request.args.get('project_id',type=int);p=None;req=[];team=[];coverage=0;error=None
    if pid:
        try:p,req,team,coverage=team_data(pid)
        except Exception as e:error=str(e)
    return render_template('team.html',projects=ps,selected_project=pid,project=p,required_skills=req,team=team,coverage=coverage,error=error)

@app.route('/allocations', methods=['GET','POST'])
def allocations():
    company_id = current_company_id()
    if request.method == 'POST':
        if current_user()['role'] != 'admin':
            flash('Administrator access is required to change allocations.','error')
            return redirect(url_for('allocations'))
        c=cur=None
        try:
            eid=int(request.form['employee_id']); pid=int(request.form['project_id']); amt=float(request.form['allocation'])
            if not 0 < amt <= 100: raise ValueError('Allocation must be between 0.01% and 100%.')
            c=db(); cur=c.cursor()
            cur.execute('SELECT employee_id,workload FROM employees WHERE employee_id=%s AND company_id=%s FOR UPDATE',(eid,company_id))
            if not cur.fetchone(): raise ValueError('Employee not found in your company.')
            cur.execute('SELECT project_id FROM projects WHERE project_id=%s AND company_id=%s FOR UPDATE',(pid,company_id))
            if not cur.fetchone(): raise ValueError('Project not found in your company.')
            cur.execute('SELECT allocation_id FROM allocations WHERE employee_id=%s AND project_id=%s AND company_id=%s',(eid,pid,company_id))
            if cur.fetchone(): raise ValueError('Existing allocation found; modify it instead.')
            cur.execute('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE employee_id=%s AND company_id=%s',(eid,company_id))
            employee_load=float(cur.fetchone()[0] or 0)
            if employee_load+amt>100.0001: raise ValueError(f'Allocation exceeds employee capacity. Available: {max(0,100-employee_load):.2f}%.')
            cur.execute('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE project_id=%s AND company_id=%s',(pid,company_id))
            project_load=float(cur.fetchone()[0] or 0)
            if project_load+amt>100.0001: raise ValueError(f'Project allocation cannot exceed 100%. Remaining project capacity: {max(0,100-project_load):.2f}%.')
            cur.execute('INSERT INTO allocations(employee_id,project_id,allocation_percentage,company_id) VALUES(%s,%s,%s,%s) RETURNING allocation_id',(eid,pid,amt,company_id))
            aid=cur.fetchone()[0]; sync_employee(cur,eid); log_company_allocation_history(c,eid,pid,'ADD',0,amt); c.commit()
            flash(f'Allocation #{aid} created successfully.','success')
        except Exception as e:
            if c: c.rollback()
            flash(str(e),'error')
        finally:
            if cur: cur.close()
            if c: c.close()
    rows=fetchall('''SELECT a.allocation_id,e.name,p.name,a.allocation_percentage,a.allocation_date
                     FROM allocations a JOIN employees e ON e.employee_id=a.employee_id AND e.company_id=a.company_id
                     JOIN projects p ON p.project_id=a.project_id AND p.company_id=a.company_id
                     WHERE a.company_id=%s ORDER BY a.allocation_id''',(company_id,))
    return render_template('allocations.html',allocations=rows,
        employees=fetchall('SELECT employee_id,name,(100-workload) AS availability,workload FROM employees WHERE company_id=%s ORDER BY employee_id',(company_id,)),
        projects=fetchall('SELECT project_id,name FROM projects WHERE company_id=%s ORDER BY project_id',(company_id,)))

@app.post('/allocations/<int:aid>/modify')
def modify_allocation(aid):
    if current_user()['role'] != 'admin': flash('Administrator access is required to modify allocations.','error'); return redirect(url_for('allocations'))
    company_id=current_company_id(); c=db(); cur=c.cursor()
    try:
        new_amt=float(request.form['allocation'])
        if not 0<new_amt<=100: raise ValueError('Allocation must be between 0.01% and 100%.')
        cur.execute('SELECT employee_id,project_id,allocation_percentage FROM allocations WHERE allocation_id=%s AND company_id=%s FOR UPDATE',(aid,company_id))
        row=cur.fetchone()
        if not row: raise ValueError('Allocation not found in your company.')
        eid,pid,old_amt=row
        cur.execute('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE employee_id=%s AND company_id=%s AND allocation_id<>%s',(eid,company_id,aid))
        other_employee=float(cur.fetchone()[0] or 0)
        if other_employee+new_amt>100.0001: raise ValueError(f'Employee capacity exceeded. Maximum for this allocation: {max(0,100-other_employee):.2f}%.')
        cur.execute('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE project_id=%s AND company_id=%s AND allocation_id<>%s',(pid,company_id,aid))
        other_project=float(cur.fetchone()[0] or 0)
        if other_project+new_amt>100.0001: raise ValueError(f'Project capacity exceeded. Maximum for this allocation: {max(0,100-other_project):.2f}%.')
        cur.execute('UPDATE allocations SET allocation_percentage=%s WHERE allocation_id=%s AND company_id=%s',(new_amt,aid,company_id))
        sync_employee(cur,eid); log_company_allocation_history(c,eid,pid,'MODIFY',old_amt,new_amt); c.commit()
        flash(f'Allocation #{aid} modified successfully.','success')
    except Exception as e: c.rollback(); flash(str(e),'error')
    finally: cur.close(); c.close()
    return redirect(url_for('allocations'))

@app.post('/allocations/<int:aid>/delete')
def delete_allocation(aid):
    if current_user()['role'] != 'admin': flash('Administrator access is required to remove allocations.','error'); return redirect(url_for('allocations'))
    company_id=current_company_id(); c=db(); cur=c.cursor()
    try:
        cur.execute('SELECT employee_id,project_id,allocation_percentage FROM allocations WHERE allocation_id=%s AND company_id=%s FOR UPDATE',(aid,company_id))
        row=cur.fetchone()
        if not row: raise ValueError('Allocation not found in your company.')
        eid,pid,amt=row
        cur.execute('DELETE FROM allocations WHERE allocation_id=%s AND company_id=%s',(aid,company_id))
        sync_employee(cur,eid); log_company_allocation_history(c,eid,pid,'REMOVE',amt,0); c.commit()
        flash('Allocation removed successfully.','success')
    except Exception as e: c.rollback(); flash(str(e),'error')
    finally: cur.close(); c.close()
    return redirect(url_for('allocations'))

@app.route('/analytics')
def analytics(): return render_template('analytics.html',data=dashboard_data(),utilization=fetchall('SELECT employee_id,name,workload,(100-workload) AS availability FROM employees WHERE company_id=%s ORDER BY workload DESC',(current_company_id(),)))

@app.route('/history')
def history():
    rows=fetchall('''SELECT h.history_id,e.name,p.name,h.action,h.old_allocation,h.new_allocation,h.changed_at
                     FROM allocation_history h
                     JOIN employees e ON e.employee_id=h.employee_id AND e.company_id=h.company_id
                     JOIN projects p ON p.project_id=h.project_id AND p.company_id=h.company_id
                     WHERE h.company_id=%s ORDER BY h.changed_at DESC,h.history_id DESC''',(current_company_id(),))
    return feature_page('Allocation History','Complete audit trail of allocation changes.','history',{'rows':rows})

@app.route('/risk')
def risk():
    data=[]
    for pid,name,priority,req,current in project_rows():
        gap=max(float(req)-float(current),0); risk=min(100,gap*2 + ({'High':20,'Medium':10,'Low':0}.get(str(priority),0)))
        data.append(dict(name=name,priority=priority,required=float(req),current=float(current),gap=gap,risk=risk,status='CRITICAL' if risk>=75 else 'HIGH' if risk>=50 else 'MEDIUM' if risk>=25 else 'LOW'))
    return feature_page('Project Risk Analysis','Staffing risk based on allocation gaps and priority.','risk',{'rows':data})

@app.route('/forecast')
def forecast():
    rows=[]
    for pid,name,priority,req,current in project_rows():
        gap=max(float(req)-float(current),0); score=min(100,(gap/max(float(req),1))*100); status='CRITICAL DEMAND' if score>=75 else 'HIGH DEMAND' if score>=40 else 'STABLE'; forecast='SEVERE RESOURCE SHORTAGE' if score>=75 else 'RESOURCE SHORTAGE LIKELY' if score>=40 else 'NO SHORTAGE EXPECTED'
        rows.append(dict(name=name,priority=priority,current=float(current),required=float(req),gap=gap,score=score,status=status,forecast=forecast))
    return feature_page('Resource Demand Forecast','Forward-looking staffing demand and shortage signals.','forecast',{'rows':rows})

@app.route('/performance')
def performance(): return feature_page('Allocation Performance Analytics','Organization and project-level KPIs.','performance',dashboard_data())
@app.route('/trends')
def trends():
    rows=fetchall('''SELECT p.name,COALESCE(SUM(h.new_allocation-h.old_allocation),0),COUNT(h.history_id)
                     FROM projects p LEFT JOIN allocation_history h ON h.project_id=p.project_id AND h.company_id=p.company_id
                     WHERE p.company_id=%s GROUP BY p.project_id,p.name ORDER BY p.project_id''',(current_company_id(),))
    return feature_page('Allocation Trends & Historical Intelligence','Historical movement and current staffing signals.','trends',{'rows':rows,'data':dashboard_data()})

@app.route('/advisor')
def advisor():
    d=dashboard_data(); priority_rank={'Critical':4,'High':3,'Medium':2,'Low':1}; actions=sorted(d['alerts'],key=lambda x:(priority_rank.get(str(x['priority']).title(),1),x['gap']),reverse=True);return feature_page('Intelligent Resource Allocation Advisor','Decision support combining staffing gaps, capacity and history.','advisor',{'data':d,'actions':actions})
@app.route('/reallocation')
def reallocation():
    company_id=current_company_id()
    ps=fetchall('SELECT project_id,name,priority,required_allocation FROM projects WHERE company_id=%s ORDER BY project_id',(company_id,))
    pid=request.args.get('project_id',type=int); result=None
    if pid:
        try:
            p,req,recs=recommendation_data(pid)
            gap=max(float(p[3])-sum(float(x[3]) for x in fetchall('SELECT allocation_id,employee_id,project_id,allocation_percentage FROM allocations WHERE project_id=%s AND company_id=%s',(pid,company_id))),0)
            picks=[]; remaining=gap
        except Exception as e:
            return feature_page('Smart Reallocation Engine','Capacity-aware redistribution plan.','error',{'error':str(e)})
        for x in sorted(recs,key=lambda z:z['score'],reverse=True):
            safe=max(0,min(x['availability'],100-x['workload'])); amt=min(remaining,safe)
            if amt>0: picks.append((x,amt)); remaining-=amt
            if remaining<=0: break
        result={'project':p,'required':req,'gap':gap,'picks':picks,'remaining':remaining}
    return render_template('reallocation.html',projects=ps,pid=pid,result=result)

@app.route('/optimization')
def optimization():
    ps=fetchall('SELECT project_id,name,priority,required_allocation FROM projects WHERE company_id=%s ORDER BY project_id',(current_company_id(),));pid=request.args.get('project_id',type=int);result=None;error=None
    if pid:
        try:
            p,req,team,cov=team_data(pid); result={'project':p,'required':req,'team':team,'coverage':cov,'confidence':round(min(100,cov*.6+sum(x['score'] for x in team)/max(1,len(team))*.4),2)}
        except Exception as e:error=str(e)
    return render_template('optimization.html',projects=ps,pid=pid,result=result,error=error)
@app.route('/executive')
def executive(): return feature_page('Executive Resource Dashboard & KPIs','Management-level view of organizational resource health.','executive',dashboard_data())
@app.route('/validation')
def validation():
    company_id=current_company_id()
    employees=fetchall('SELECT employee_id,name,experience,availability,workload FROM employees WHERE company_id=%s ORDER BY employee_id',(company_id,))
    projects=fetchall('SELECT project_id,name,priority,required_allocation FROM projects WHERE company_id=%s ORDER BY project_id',(company_id,))
    alloc=fetchall('SELECT allocation_id,employee_id,project_id,allocation_percentage FROM allocations WHERE company_id=%s ORDER BY allocation_id',(company_id,))
    issues=[]; warnings=[]
    for eid,n,ex,av,w in employees:
        if float(ex)<0: issues.append(f'Employee {eid} ({n}): negative experience value.')
        if not 0<=float(w)<=100 or not 0<=float(av)<=100: issues.append(f'Employee {eid} ({n}): workload/availability outside 0-100%.')
        if abs(float(av)+float(w)-100)>0.01: issues.append(f'Employee {eid} ({n}): workload + availability must equal 100%.')
        actual=fetchone('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE employee_id=%s AND company_id=%s',(eid,company_id))[0]
        if abs(float(actual)-float(w))>0.01: issues.append(f'Employee {eid} ({n}): stored workload does not match allocation total ({float(actual):.2f}%).')
    for pid,n,pr,req in projects:
        if not 0<float(req)<=100: issues.append(f'Project {pid} ({n}): invalid required allocation.')
        total=float(fetchone('SELECT COALESCE(SUM(allocation_percentage),0) FROM allocations WHERE project_id=%s AND company_id=%s',(pid,company_id))[0] or 0)
        if total>100.01: issues.append(f'Project {pid} ({n}): allocation total exceeds 100% ({total:.2f}%).')
    for aid,eid,pid,pct in alloc:
        if not 0<float(pct)<=100: issues.append(f'Allocation {aid}: invalid percentage.')
    return render_template('validation.html',employees=employees,projects=projects,allocations=alloc,issues=issues,warnings=warnings)

@app.route('/api/recommendations/<int:pid>')
def api_recommend(pid):
    try:p,req,r=recommendation_data(pid);return jsonify({'project':p[1],'required_skills':req,'recommendations':r})
    except Exception as e:return jsonify({'error':str(e)}),400

@app.route('/reports')
def reports(): return feature_page('Final Project Report & Portfolio Readiness','Complete capability checklist for your SRA portfolio.','reports',{'version':33,'capabilities':['Employee, skill and project management','Employee-project matching and recommendations','Manual allocation and modification','Skill-coverage smart team allocation','Workload balancing and rebalancing','Allocation history and audit tracking','Resource utilization analytics','Project risk analysis','Resource demand forecasting','Allocation performance analytics','Historical intelligence','Intelligent allocation advisor','Smart resource reallocation','Constraint-aware optimization','Executive KPIs','System validation']})

if __name__=='__main__':
    try:
        sra.initialize_database()
        init_auth()
        repaired=repair_employee_capacity()
        if repaired:
            print(f'Capacity consistency repair: {repaired} employee record(s) normalized.')
    except Exception as e:print('Database initialization warning:',e)
    app.run(debug=False,host='127.0.0.1',port=5000)
