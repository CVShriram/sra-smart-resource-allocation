# ============================================================
# SMART RESOURCE ALLOCATION PLATFORM
# VERSION 32 - SYSTEM HARDENING & VALIDATION
#
# PostgreSQL + Python
#
# FEATURES
# ------------------------------------------------------------
# 1.  View Employees
# 2.  View Skills
# 3.  View Projects
# 4.  Test Employee-Project Match
# 5.  Recommend Employees
# 6.  Allocate Employee to Project
# 7.  Remove Allocation
# 8.  View Current Allocations
# 9.  Project Allocation Dashboard
# 10. Skill-Coverage Smart Team Allocation
# 10.1 Intelligent Priority + Workload Optimization
# 10.2 Workload Balance Analysis
# 11. Exit
#
# ADMIN / DATA MANAGEMENT
# 12. Add Employee
# 13. Add Skill
# 14. Add Project
# 15. Assign Skill to Employee
# 16. Assign Skill to Project
# 17. Modify Existing Allocation
# 18. Smart Rebalance Project
# 19. View Allocation History
# 20. Resource Utilization Analytics
# 21. Project Risk Analysis
# 22. Resource Demand Forecast
# 23. Resource Allocation Performance Analytics
# 24. Allocation Trend & Historical Intelligence
# 25. Intelligent Resource Allocation Advisor
# ============================================================

import psycopg2
import os 

from itertools import combinations
from dotenv import load_dotenv

# ============================================================
# DATABASE CONNECTION
# ============================================================

load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "resource_allocation"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432")
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allocations (

            allocation_id SERIAL PRIMARY KEY,

            employee_id INT NOT NULL,

            project_id INT NOT NULL,

            allocation_percentage NUMERIC(5,2) NOT NULL,

            allocation_date DATE DEFAULT CURRENT_DATE,

            CONSTRAINT fk_allocation_employee
                FOREIGN KEY (employee_id)
                REFERENCES employees(employee_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_allocation_project
                FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
                ON DELETE CASCADE,

            CONSTRAINT unique_employee_project
                UNIQUE (employee_id, project_id),

            CONSTRAINT valid_allocation_percentage
                CHECK (
                    allocation_percentage > 0
                    AND allocation_percentage <= 100
                )
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allocation_history (
            history_id SERIAL PRIMARY KEY,
            employee_id INT NOT NULL,
            project_id INT NOT NULL,
            action VARCHAR(20) NOT NULL,
            old_allocation NUMERIC(5,2) DEFAULT 0,
            new_allocation NUMERIC(5,2) DEFAULT 0,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id)
                REFERENCES employees(employee_id)
                ON DELETE CASCADE,
            FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
                ON DELETE CASCADE
        );
    """)

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# VERSION 23 - ALLOCATION AUDIT LOGGING
# ============================================================

def log_allocation_history(
    connection,
    employee_id,
    project_id,
    action,
    old_allocation,
    new_allocation
):
    """Record an allocation change inside the caller's transaction."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO allocation_history
            (
                employee_id,
                project_id,
                action,
                old_allocation,
                new_allocation
            )
            VALUES (%s, %s, %s, %s, %s);
        """, (
            employee_id,
            project_id,
            action,
            old_allocation,
            new_allocation
        ))
    finally:
        cursor.close()


# ============================================================
# VIEW EMPLOYEES
# ============================================================

def view_employees():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            e.employee_id,
            e.name,
            e.experience,
            e.availability,
            e.workload,

            COALESCE(
                STRING_AGG(
                    s.skill_name,
                    ', '
                    ORDER BY s.skill_name
                ),
                'No skills'
            )

        FROM employees e

        LEFT JOIN employee_skills es
            ON e.employee_id = es.employee_id

        LEFT JOIN skills s
            ON es.skill_id = s.skill_id

        GROUP BY
            e.employee_id,
            e.name,
            e.experience,
            e.availability,
            e.workload

        ORDER BY e.employee_id;
    """)

    employees = cursor.fetchall()

    print("\n")
    print("=" * 70)
    print("                         EMPLOYEES")
    print("=" * 70)

    if not employees:
        print("No employees found.")

    for employee in employees:

        print("\n------------------------------------------------------------")

        print("ID:", employee[0])
        print("Name:", employee[1])
        print("Experience:", employee[2], "years")
        print("Availability:", employee[3], "%")
        print("Workload:", employee[4], "%")
        print("Skills:", employee[5])

    print("-" * 70)

    cursor.close()
    connection.close()


# ============================================================
# VIEW SKILLS
# ============================================================

def view_skills():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            skill_id,
            skill_name
        FROM skills
        ORDER BY skill_id;
    """)

    skills = cursor.fetchall()

    print("\n")
    print("=" * 70)
    print("                           SKILLS")
    print("=" * 70)

    if not skills:
        print("No skills found.")

    for skill in skills:

        print(
            "ID:",
            skill[0],
            "| Skill:",
            skill[1]
        )

    print("-" * 70)

    cursor.close()
    connection.close()


# ============================================================
# GET EMPLOYEE SKILLS
# ============================================================

def get_employee_skills(employee_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            s.skill_name

        FROM employee_skills es

        JOIN skills s
            ON es.skill_id = s.skill_id

        WHERE es.employee_id = %s

        ORDER BY s.skill_name;
    """, (employee_id,))

    skills = cursor.fetchall()

    cursor.close()
    connection.close()

    return [
        skill[0]
        for skill in skills
    ]


# ============================================================
# GET PROJECT SKILLS
# ============================================================

def get_project_skills(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            s.skill_name

        FROM project_skills ps

        JOIN skills s
            ON ps.skill_id = s.skill_id

        WHERE ps.project_id = %s

        ORDER BY s.skill_id;
    """, (project_id,))

    skills = cursor.fetchall()

    cursor.close()
    connection.close()

    return [
        skill[0]
        for skill in skills
    ]


# ============================================================
# VIEW PROJECTS
# ============================================================

def view_projects():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_id,
            name,
            priority,
            required_allocation

        FROM projects

        ORDER BY project_id;
    """)

    projects = cursor.fetchall()

    print("\n")
    print("=" * 70)
    print("                          PROJECTS")
    print("=" * 70)

    if not projects:
        print("No projects found.")

    for project in projects:

        project_id = project[0]

        print("\n------------------------------------------------------------")

        print("ID:", project_id)
        print("Project:", project[1])
        print("Priority:", project[2])
        print(
            "Required Allocation:",
            project[3],
            "%"
        )

        skills = get_project_skills(project_id)

        print(
            "Required Skills:",
            ", ".join(skills)
            if skills
            else "No required skills"
        )

    print("-" * 70)

    cursor.close()
    connection.close()


# ============================================================
# GET PROJECT DETAILS
# ============================================================

def get_project_details(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_id,
            name,
            priority,
            required_allocation

        FROM projects

        WHERE project_id = %s;
    """, (project_id,))

    project = cursor.fetchone()

    cursor.close()
    connection.close()

    return project


# ============================================================
# GET EMPLOYEE DETAILS
# ============================================================

def get_employee_details(employee_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            employee_id,
            name,
            experience,
            availability,
            workload

        FROM employees

        WHERE employee_id = %s;
    """, (employee_id,))

    employee = cursor.fetchone()

    cursor.close()
    connection.close()

    return employee


# ============================================================
# SKILL MATCH CALCULATION
# ============================================================

def calculate_skill_match(
    employee_skills,
    project_skills
):

    if not project_skills:
        return 0.0

    employee_set = set(employee_skills)
    project_set = set(project_skills)

    matched = (
        employee_set &
        project_set
    )

    return (
        len(matched)
        /
        len(project_set)
    ) * 100


# ============================================================
# FINAL EMPLOYEE SCORE
# ============================================================

def calculate_match_score(
    skill_match,
    availability,
    workload,
    experience
):

    skill_match = float(skill_match)
    availability = float(availability)
    workload = float(workload)
    experience = float(experience)

    workload_score = 100 - workload

    experience_score = min(
        (experience / 10) * 100,
        100
    )

    score = (

        skill_match * 0.50

        +

        availability * 0.20

        +

        workload_score * 0.20

        +

        experience_score * 0.10
    )

    return round(score, 2)


# ============================================================
# TEST MATCHING
# ============================================================

def test_matching():

    print("\n")
    print("=" * 70)
    print("                  TEST EMPLOYEE-PROJECT MATCH")
    print("=" * 70)

    try:

        project_id = int(
            input("\nEnter Project ID: ")
        )

        employee_id = int(
            input("Enter Employee ID: ")
        )

    except ValueError:

        print("\nPlease enter valid numeric IDs.")
        return

    project = get_project_details(project_id)
    employee = get_employee_details(employee_id)

    if project is None:

        print("\nProject not found.")
        return

    if employee is None:

        print("\nEmployee not found.")
        return

    project_skills = get_project_skills(project_id)
    employee_skills = get_employee_skills(employee_id)

    skill_match = calculate_skill_match(
        employee_skills,
        project_skills
    )

    score = calculate_match_score(
        skill_match,
        employee[3],
        employee[4],
        employee[2]
    )

    print("\n")
    print("=" * 70)
    print("                       MATCH RESULT")
    print("=" * 70)

    print("\nProject:", project[1])

    print(
        "Required Skills:",
        ", ".join(project_skills)
    )

    print("\nEmployee:", employee[1])

    print(
        "Employee Skills:",
        ", ".join(employee_skills)
    )

    print(
        "\nSkill Match:",
        round(skill_match, 2),
        "%"
    )

    print(
        "Availability:",
        employee[3],
        "%"
    )

    print(
        "Workload:",
        employee[4],
        "%"
    )

    print(
        "Experience:",
        employee[2],
        "years"
    )

    print(
        "\nFINAL MATCH SCORE:",
        score,
        "%"
    )

    print("=" * 70)


# ============================================================
# RECOMMEND EMPLOYEES
# ============================================================

def recommend_employees():

    print("\n")
    print("=" * 70)
    print("                    EMPLOYEE RECOMMENDATION")
    print("=" * 70)

    try:

        project_id = int(
            input("\nEnter Project ID: ")
        )

    except ValueError:

        print("\nInvalid Project ID.")
        return

    project = get_project_details(project_id)

    if project is None:

        print("\nProject not found.")
        return

    project_skills = get_project_skills(project_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            employee_id,
            name,
            experience,
            availability,
            workload

        FROM employees

        ORDER BY employee_id;
    """)

    employees = cursor.fetchall()

    cursor.close()
    connection.close()

    recommendations = []

    for employee in employees:

        employee_skills = get_employee_skills(
            employee[0]
        )

        skill_match = calculate_skill_match(
            employee_skills,
            project_skills
        )

        score = calculate_match_score(
            skill_match,
            employee[3],
            employee[4],
            employee[2]
        )

        recommendations.append({

            "id": employee[0],
            "name": employee[1],
            "experience": float(employee[2]),
            "availability": float(employee[3]),
            "workload": float(employee[4]),
            "skill_match": skill_match,
            "score": score,
            "skills": employee_skills
        })

    recommendations.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print(
        "\nProject:",
        project[1]
    )

    print(
        "Required Skills:",
        ", ".join(project_skills)
    )

    print()

    rank = 1

    for employee in recommendations:

        print(
            "Rank",
            rank,
            "|",
            employee["name"]
        )

        print(
            "  Skills:",
            ", ".join(employee["skills"])
        )

        print(
            "  Skill Match:",
            round(
                employee["skill_match"],
                2
            ),
            "%"
        )

        print(
            "  Availability:",
            employee["availability"],
            "%"
        )

        print(
            "  Workload:",
            employee["workload"],
            "%"
        )

        print(
            "  Experience:",
            employee["experience"],
            "years"
        )

        print(
            "  Match Score:",
            employee["score"],
            "%"
        )

        print("-" * 70)

        rank += 1


# ============================================================
# EXISTING ALLOCATION
# ============================================================

def get_existing_allocation(
    employee_id,
    project_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            allocation_id,
            allocation_percentage

        FROM allocations

        WHERE employee_id = %s
        AND project_id = %s;
    """, (
        employee_id,
        project_id
    ))

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return result


# ============================================================
# CURRENT PROJECT ALLOCATION
# ============================================================

def get_current_project_allocation(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(
                SUM(allocation_percentage),
                0
            )

        FROM allocations

        WHERE project_id = %s;
    """, (project_id,))

    total = float(
        cursor.fetchone()[0]
    )

    cursor.close()
    connection.close()

    return total


# ============================================================
# VIEW ALLOCATIONS
# ============================================================

def view_allocations():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            a.allocation_id,
            e.name,
            p.name,
            a.allocation_percentage,
            a.allocation_date

        FROM allocations a

        JOIN employees e
            ON a.employee_id = e.employee_id

        JOIN projects p
            ON a.project_id = p.project_id

        ORDER BY a.allocation_id;
    """)

    allocations = cursor.fetchall()

    print("\n")
    print("=" * 70)
    print("                    CURRENT ALLOCATIONS")
    print("=" * 70)

    if not allocations:

        print("\nNo allocations found.")

    for allocation in allocations:

        print("\nAllocation ID:", allocation[0])
        print("Employee:", allocation[1])
        print("Project:", allocation[2])
        print(
            "Allocation:",
            allocation[3],
            "%"
        )
        print("Date:", allocation[4])

        print("-" * 70)

    cursor.close()
    connection.close()


# ============================================================
# VERSION 20 - ALLOCATION CONFLICT DETECTION
# ============================================================

def get_employee_project_allocation_total(employee_id, project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(allocation_percentage), 0)
        FROM allocations
        WHERE employee_id = %s
        AND project_id = %s;
    """, (
        employee_id,
        project_id
    ))

    total = float(cursor.fetchone()[0])

    cursor.close()
    connection.close()

    return total


def check_allocation_conflict(
    employee_id,
    project_id,
    proposed_allocation,
    allow_existing_project=False
):
    """
    Check whether a proposed allocation creates a business-rule conflict.

    Returns a dictionary containing:
    - conflict: True/False
    - reason: human-readable explanation
    - existing_allocation: current allocation on this project
    - current_workload: current employee workload
    - available_capacity: safe remaining capacity
    - projected_workload: workload after proposed allocation
    - excess: amount above safe capacity
    """

    employee = get_employee_details(employee_id)

    if employee is None:

        return {
            "conflict": True,
            "reason": "Employee not found.",
            "existing_allocation": 0.0,
            "current_workload": 0.0,
            "available_capacity": 0.0,
            "projected_workload": 0.0,
            "excess": 0.0
        }

    current_workload = float(employee[4])
    availability = float(employee[3])
    existing_allocation = get_employee_project_allocation_total(
        employee_id,
        project_id
    )

    projected_workload = current_workload + proposed_allocation
    safe_capacity = min(
        availability,
        max(0.0, 100.0 - current_workload)
    )

    # Existing allocation on the same project is treated as a duplicate
    # by default. The caller can explicitly allow it if needed.
    if existing_allocation > 0 and not allow_existing_project:

        return {
            "conflict": True,
            "reason": "Employee is already allocated to this project.",
            "existing_allocation": existing_allocation,
            "current_workload": current_workload,
            "available_capacity": safe_capacity,
            "projected_workload": projected_workload,
            "excess": max(0.0, proposed_allocation - safe_capacity)
        }

    if proposed_allocation > availability:

        return {
            "conflict": True,
            "reason": "Requested allocation exceeds available capacity.",
            "existing_allocation": existing_allocation,
            "current_workload": current_workload,
            "available_capacity": safe_capacity,
            "projected_workload": projected_workload,
            "excess": proposed_allocation - availability
        }

    if projected_workload > 100.0:

        return {
            "conflict": True,
            "reason": "Projected workload would exceed 100%.",
            "existing_allocation": existing_allocation,
            "current_workload": current_workload,
            "available_capacity": safe_capacity,
            "projected_workload": projected_workload,
            "excess": projected_workload - 100.0
        }

    return {
        "conflict": False,
        "reason": "Allocation is safe.",
        "existing_allocation": existing_allocation,
        "current_workload": current_workload,
        "available_capacity": safe_capacity,
        "projected_workload": projected_workload,
        "excess": 0.0
    }


def print_allocation_conflict(
    employee,
    project,
    proposed_allocation,
    conflict
):

    print("\\n")
    print("=" * 70)
    print("                    ALLOCATION CONFLICT")
    print("=" * 70)

    print("\\nEmployee:", employee[1])
    print("Project:", project[1])

    print(
        "\\nCurrent Workload:",
        round(conflict["current_workload"], 2),
        "%"
    )

    print(
        "Available Capacity:",
        round(conflict["available_capacity"], 2),
        "%"
    )

    print(
        "Requested Allocation:",
        round(proposed_allocation, 2),
        "%"
    )

    print(
        "Projected Workload:",
        round(conflict["projected_workload"], 2),
        "%"
    )

    if conflict["existing_allocation"] > 0:

        print(
            "Existing Project Allocation:",
            round(conflict["existing_allocation"], 2),
            "%"
        )

    print("\\n❌ CONFLICT DETECTED")
    print("Reason:", conflict["reason"])

    if conflict["existing_allocation"] > 0:

        combined = (
            conflict["existing_allocation"]
            + proposed_allocation
        )

        print(
            "\\nSuggested Combined Allocation:",
            round(combined, 2),
            "%"
        )

        if combined <= conflict["available_capacity"]:

            print(
                "Recommendation: Update the existing allocation instead "
                "of creating a duplicate record."
            )

        else:

            print(
                "Recommendation: Reduce the combined allocation or "
                "select another employee."
            )

    else:

        print(
            "\\nMaximum Safe Allocation:",
            round(conflict["available_capacity"], 2),
            "%"
        )

        print(
            "Excess Allocation:",
            round(conflict["excess"], 2),
            "%"
        )

        print(
            "Recommendation: Reduce allocation or select another employee."
        )


def preflight_team_allocation_conflicts(
    allocations,
    project_id
):
    """Validate every proposed team allocation before any INSERT occurs."""

    conflicts = []

    project = get_project_details(project_id)

    if project is None:

        conflicts.append({
            "employee": None,
            "project": None,
            "allocation": 0.0,
            "details": {
                "conflict": True,
                "reason": "Project not found."
            }
        })

        return conflicts

    # Track workload sequentially in memory so the combined team plan
    # cannot overload an employee even if the database was changed earlier
    # in the same transaction.
    projected_workloads = {}

    for item in allocations:

        employee = item["employee"]
        employee_id = employee["id"]
        proposed = float(item["allocation"])

        if employee_id not in projected_workloads:

            projected_workloads[employee_id] = float(employee["workload"])

        current = projected_workloads[employee_id]
        availability = float(employee["availability"])

        existing = get_employee_project_allocation_total(
            employee_id,
            project_id
        )

        if existing > 0:

            conflicts.append({
                "employee": employee,
                "project": project,
                "allocation": proposed,
                "details": {
                    "conflict": True,
                    "reason": "Employee is already allocated to this project.",
                    "existing_allocation": existing,
                    "current_workload": current,
                    "available_capacity": min(
                        availability,
                        max(0.0, 100.0 - current)
                    ),
                    "projected_workload": current + proposed,
                    "excess": max(0.0, proposed - availability)
                }
            })

            continue

        if proposed > availability:

            conflicts.append({
                "employee": employee,
                "project": project,
                "allocation": proposed,
                "details": {
                    "conflict": True,
                    "reason": "Requested allocation exceeds available capacity.",
                    "existing_allocation": existing,
                    "current_workload": current,
                    "available_capacity": min(
                        availability,
                        max(0.0, 100.0 - current)
                    ),
                    "projected_workload": current + proposed,
                    "excess": proposed - availability
                }
            })

            continue

        if current + proposed > 100.0:

            conflicts.append({
                "employee": employee,
                "project": project,
                "allocation": proposed,
                "details": {
                    "conflict": True,
                    "reason": "Projected workload would exceed 100%.",
                    "existing_allocation": existing,
                    "current_workload": current,
                    "available_capacity": min(
                        availability,
                        max(0.0, 100.0 - current)
                    ),
                    "projected_workload": current + proposed,
                    "excess": current + proposed - 100.0
                }
            })

            continue

        projected_workloads[employee_id] = current + proposed

    return conflicts


# ============================================================
# MANUAL ALLOCATION
# ============================================================

def allocate_employee():

    print("\n")
    print("=" * 70)
    print("                    MANUAL ALLOCATION")
    print("=" * 70)

    try:

        employee_id = int(
            input("\nEnter Employee ID: ")
        )

        project_id = int(
            input("Enter Project ID: ")
        )

    except ValueError:

        print("\nInvalid ID.")
        return

    employee = get_employee_details(employee_id)
    project = get_project_details(project_id)

    if employee is None:

        print("\nEmployee not found.")
        return

    if project is None:

        print("\nProject not found.")
        return

    existing = get_existing_allocation(
        employee_id,
        project_id
    )

    if existing:

        print(
            "\n⚠️ Employee is already allocated "
            "to this project."
        )

        print(
            "Existing Allocation:",
            round(float(existing[1]), 2),
            "%"
        )

        print(
            "Recommendation: Update the existing allocation "
            "instead of creating a duplicate record."
        )

        return

    try:

        allocation = float(
            input(
                "\nEnter allocation percentage: "
            )
        )

    except ValueError:

        print("\nInvalid allocation.")
        return

    availability = float(employee[3])
    workload = float(employee[4])

    if allocation <= 0:

        print(
            "\nAllocation must be greater than 0."
        )

        return

    conflict = check_allocation_conflict(
        employee_id,
        project_id,
        allocation
    )

    if conflict["conflict"]:

        print_allocation_conflict(
            employee,
            project,
            allocation,
            conflict
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO allocations
            (
                employee_id,
                project_id,
                allocation_percentage
            )

            VALUES
            (
                %s,
                %s,
                %s
            );
        """, (
            employee_id,
            project_id,
            allocation
        ))

        cursor.execute("""
            UPDATE employees

            SET
                availability =
                    availability - %s,

                workload =
                    workload + %s

            WHERE employee_id = %s;
        """, (
            allocation,
            allocation,
            employee_id
        ))

        log_allocation_history(
            connection,
            employee_id,
            project_id,
            "ADD",
            0.0,
            allocation
        )

        connection.commit()

        print(
            "\n✅ Employee successfully allocated."
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Allocation failed:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# REMOVE ALLOCATION
# ============================================================

def remove_allocation():

    view_allocations()

    try:

        allocation_id = int(
            input(
                "\nEnter Allocation ID to remove: "
            )
        )

    except ValueError:

        print("\nInvalid ID.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            employee_id,
            project_id,
            allocation_percentage

        FROM allocations

        WHERE allocation_id = %s;
    """, (allocation_id,))

    allocation = cursor.fetchone()

    if allocation is None:

        print("\nAllocation not found.")

        cursor.close()
        connection.close()

        return

    employee_id = allocation[0]
    project_id = allocation[1]
    percentage = float(allocation[2])

    try:

        cursor.execute("""
            DELETE FROM allocations

            WHERE allocation_id = %s;
        """, (allocation_id,))

        cursor.execute("""
            UPDATE employees

            SET
                availability =
                    LEAST(
                        100,
                        availability + %s
                    ),

                workload =
                    GREATEST(
                        0,
                        workload - %s
                    )

            WHERE employee_id = %s;
        """, (
            percentage,
            percentage,
            employee_id
        ))

        log_allocation_history(
            connection,
            employee_id,
            project_id,
            "REMOVE",
            percentage,
            0.0
        )

        connection.commit()

        print(
            "\n✅ Allocation removed."
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Removal failed:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# VERSION 22 - MODIFY EXISTING ALLOCATION
# ============================================================

def modify_allocation():

    print("\n")
    print("=" * 70)
    print("                 MODIFY EXISTING ALLOCATION")
    print("=" * 70)

    try:
        employee_id = int(input("\nEnter Employee ID: "))
        project_id = int(input("Enter Project ID: "))
    except ValueError:
        print("\n❌ Please enter valid numeric IDs.")
        return

    employee = get_employee_details(employee_id)
    project = get_project_details(project_id)

    if employee is None:
        print("\n❌ Employee not found.")
        return

    if project is None:
        print("\n❌ Project not found.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                allocation_id,
                allocation_percentage
            FROM allocations
            WHERE employee_id = %s
            AND project_id = %s
            FOR UPDATE;
        """, (employee_id, project_id))

        existing = cursor.fetchone()

        if existing is None:
            print("\n❌ No allocation exists for this employee on this project.")
            return

        allocation_id = existing[0]
        current_allocation = float(existing[1])
        current_availability = float(employee[3])
        current_workload = float(employee[4])

        print("\nEmployee:", employee[1])
        print("Project:", project[1])
        print("Current Allocation:", round(current_allocation, 2), "%")
        print("Current Availability:", round(current_availability, 2), "%")
        print("Current Workload:", round(current_workload, 2), "%")

        try:
            new_allocation = float(
                input("\nEnter new allocation percentage: ")
            )
        except ValueError:
            print("\n❌ Invalid allocation percentage.")
            return

        if new_allocation <= 0:
            print("\n❌ Allocation must be greater than 0%.")
            return

        if new_allocation > 100:
            print("\n❌ Allocation cannot exceed 100%.")
            return

        change = new_allocation - current_allocation

        # Increasing an allocation consumes additional availability.
        if change > 0:
            if change > current_availability:
                print("\n❌ Allocation increase exceeds available capacity.")
                print(
                    "Additional Required:",
                    round(change, 2),
                    "%"
                )
                print(
                    "Available Capacity:",
                    round(current_availability, 2),
                    "%"
                )
                return

            projected_workload = current_workload + change

            if projected_workload > 100:
                print("\n❌ Projected workload would exceed 100%.")
                print(
                    "Projected Workload:",
                    round(projected_workload, 2),
                    "%"
                )
                return

        else:
            projected_workload = current_workload + change

            if projected_workload < 0:
                print("\n❌ Resulting workload cannot be negative.")
                return

        projected_availability = current_availability - change

        if projected_availability < 0:
            print("\n❌ Resulting availability cannot be negative.")
            return

        print("\n")
        print("=" * 70)
        print("                    MODIFICATION PREVIEW")
        print("=" * 70)
        print("\nEmployee:", employee[1])
        print("Project:", project[1])
        print(
            "\nAllocation:",
            round(current_allocation, 2),
            "% →",
            round(new_allocation, 2),
            "%"
        )
        print(
            "Availability:",
            round(current_availability, 2),
            "% →",
            round(projected_availability, 2),
            "%"
        )
        print(
            "Workload:",
            round(current_workload, 2),
            "% →",
            round(projected_workload, 2),
            "%"
        )

        if change > 0:
            print("\n📈 Allocation increased by", round(change, 2), "%")
        elif change < 0:
            print("\n📉 Allocation reduced by", round(abs(change), 2), "%")
        else:
            print("\nℹ️ New allocation is the same as the current allocation.")

        confirmation = input("\nApply this modification? (Y/N): ")

        if confirmation.lower() != "y":
            print("\nModification cancelled.")
            return

        cursor.execute("""
            UPDATE allocations
            SET allocation_percentage = %s
            WHERE allocation_id = %s;
        """, (new_allocation, allocation_id))

        cursor.execute("""
            UPDATE employees
            SET
                availability = availability - %s,
                workload = workload + %s
            WHERE employee_id = %s;
        """, (change, change, employee_id))

        if abs(change) > 0.000001:
            log_allocation_history(
                connection,
                employee_id,
                project_id,
                "MODIFY",
                current_allocation,
                new_allocation
            )

        connection.commit()

        print("\n")
        print("=" * 70)
        print("              ALLOCATION MODIFIED SUCCESSFULLY")
        print("=" * 70)
        print("\nEmployee:", employee[1])
        print("Project:", project[1])
        print("Old Allocation:", round(current_allocation, 2), "%")
        print("New Allocation:", round(new_allocation, 2), "%")
        print("Availability Now:", round(projected_availability, 2), "%")
        print("Workload Now:", round(projected_workload, 2), "%")
        print("\n✅ Database successfully updated.")

    except Exception as error:
        connection.rollback()
        print("\n❌ Allocation modification failed.")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()


# ============================================================
# PROJECT DASHBOARD
# ============================================================

def project_allocation_dashboard():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            project_id,
            name,
            priority,
            required_allocation

        FROM projects

        ORDER BY project_id;
    """)

    projects = cursor.fetchall()

    print("\n")
    print("=" * 70)
    print("                 PROJECT ALLOCATION DASHBOARD")
    print("=" * 70)

    for project in projects:

        project_id = project[0]

        required = float(project[3])

        total = get_current_project_allocation(
            project_id
        )

        remaining = required - total

        if remaining > 0:
            status = "UNDERSTAFFED"

        elif remaining < 0:
            status = "OVERSTAFFED"

        else:
            status = "FULLY STAFFED"

        print("\nProject:", project[1])
        print("Priority:", project[2])
        print("Required:", required, "%")
        print("Allocated:", round(total, 2), "%")

        print(
            "Remaining:",
            round(
                max(0, remaining),
                2
            ),
            "%"
        )

        print("Status:", status)

        skills = get_project_skills(project_id)

        print(
            "Required Skills:",
            ", ".join(skills)
        )

        cursor.execute("""
            SELECT
                e.name,
                a.allocation_percentage

            FROM allocations a

            JOIN employees e
                ON a.employee_id = e.employee_id

            WHERE a.project_id = %s

            ORDER BY e.name;
        """, (project_id,))

        assigned = cursor.fetchall()

        if assigned:

            print("\nAssigned Employees:")

            for employee in assigned:

                print(
                    " ",
                    employee[0],
                    "→",
                    employee[1],
                    "%"
                )

        else:

            print(
                "\nNo employees assigned."
            )

        print("-" * 70)

    cursor.close()
    connection.close()


# ============================================================
# GET AVAILABLE CANDIDATES
# ============================================================

def get_available_candidates(project_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            employee_id,
            name,
            experience,
            availability,
            workload

        FROM employees

        WHERE availability > 0

        ORDER BY employee_id;
    """)

    employees = cursor.fetchall()

    cursor.close()
    connection.close()

    project_skills = set(
        get_project_skills(project_id)
    )

    candidates = []

    for employee in employees:

        employee_id = employee[0]

        if get_existing_allocation(
            employee_id,
            project_id
        ) is not None:

            continue

        employee_skills = set(
            get_employee_skills(
                employee_id
            )
        )

        matched_skills = (
            employee_skills &
            project_skills
        )

        if not matched_skills:
            continue

        skill_match = (
            len(matched_skills)
            /
            len(project_skills)
        ) * 100

        score = calculate_match_score(
            skill_match,
            employee[3],
            employee[4],
            employee[2]
        )

        candidates.append({

            "id": employee_id,

            "name": employee[1],

            "experience": float(
                employee[2]
            ),

            "availability": float(
                employee[3]
            ),

            "workload": float(
                employee[4]
            ),

            "skills": employee_skills,

            "matched_skills":
                matched_skills,

            "skill_match":
                skill_match,

            "score":
                score
        })

    return candidates


# ============================================================
# FIND BEST TEAM
# ============================================================

def find_best_team(
    candidates,
    required_skills,
    required_allocation
):

    required_skills = set(
        required_skills
    )

    best_team = None
    best_coverage = -1
    best_score = -1
    best_size = 999

    max_team_size = min(
        5,
        len(candidates)
    )

    for team_size in range(
        1,
        max_team_size + 1
    ):

        for combination in combinations(
            candidates,
            team_size
        ):

            covered_skills = set()

            for employee in combination:

                covered_skills.update(
                    employee["matched_skills"]
                )

            coverage = (
                len(
                    covered_skills &
                    required_skills
                )
                /
                len(required_skills)
            ) * 100

            if coverage == 0:
                continue

            average_score = (
                sum(
                    employee["score"]
                    for employee in combination
                )
                /
                len(combination)
            )

            average_workload = (
                sum(
                    employee["workload"]
                    for employee in combination
                )
                /
                len(combination)
            )

            workload_bonus = (
                100 -
                average_workload
            )

            size_bonus = max(
                0,
                20 - team_size * 5
            )

            team_score = (

                coverage * 0.60

                +

                average_score * 0.25

                +

                workload_bonus * 0.10

                +

                size_bonus * 0.05
            )

            if coverage > best_coverage:

                best_team = combination
                best_coverage = coverage
                best_score = team_score
                best_size = team_size

            elif coverage == best_coverage:

                if team_score > best_score:

                    best_team = combination
                    best_score = team_score
                    best_size = team_size

                elif (
                    team_score == best_score
                    and team_size < best_size
                ):

                    best_team = combination
                    best_size = team_size

    return (
        best_team,
        best_coverage,
        best_score
    )


# ============================================================
# SMART ALLOCATION OPTIMIZER
# ============================================================

def optimize_team_allocations(best_team, required_allocation, project_priority):
    """
    Version 18 workload-aware allocation optimizer.

    Allocation is influenced by:
      - project priority
      - employee match score
      - matched skill count
      - availability
      - remaining capacity
      - current workload

    Workload balancing is explicitly rewarded so that employees with
    lower current workloads receive a stronger share when skill fit is
    comparable. Employees above 85% workload are treated as high-load
    and employees above 95% are avoided unless necessary.
    """

    if not best_team or required_allocation <= 0:
        return [], 0.0, "No allocation required"

    priority = str(project_priority).strip().capitalize()

    if priority == "High":
        skill_weight = 16.0
        match_weight = 0.50
        availability_weight = 0.10
        capacity_weight = 0.24
        workload_balance_weight = 0.16
        priority_description = (
            "HIGH priority → stronger emphasis on skill fit and match score, "
            "while still balancing workload"
        )

    elif priority == "Low":
        skill_weight = 8.0
        match_weight = 0.35
        availability_weight = 0.25
        capacity_weight = 0.25
        workload_balance_weight = 0.30
        priority_description = (
            "LOW priority → stronger emphasis on availability, capacity, "
            "and workload balance"
        )

    else:
        priority = "Medium"
        skill_weight = 10.0
        match_weight = 0.45
        availability_weight = 0.18
        capacity_weight = 0.27
        workload_balance_weight = 0.25
        priority_description = (
            "MEDIUM priority → balanced skill, match, capacity, "
            "and workload optimization"
        )

    employees = []

    # Average workload of the selected team gives us a reference point.
    team_workloads = [float(e["workload"]) for e in best_team]
    average_team_workload = (
        sum(team_workloads) / len(team_workloads)
        if team_workloads else 0.0
    )

    for employee in best_team:

        availability = max(0.0, float(employee["availability"]))
        workload = max(0.0, min(100.0, float(employee["workload"])))

        remaining_capacity = max(
            0.0,
            min(
                availability,
                100.0 - workload
            )
        )

        # Employees above 95% workload are not used when there is another
        # feasible employee. They can still be used if the selected team
        # has no other capacity.
        if remaining_capacity <= 0:
            continue

        skill_count = len(employee["matched_skills"])
        match_score = float(employee["score"])

        # Lower workload receives a higher balance score.
        workload_balance_score = 100.0 - workload

        # Employees below the selected team's average workload get a small
        # additional balancing benefit; overloaded employees get less.
        relative_balance = max(
            0.0,
            min(
                100.0,
                50.0 + (average_team_workload - workload)
            )
        )

        # Strong penalty for very high workload.
        overload_penalty = 0.0
        if workload >= 95.0:
            overload_penalty = 30.0
        elif workload >= 85.0:
            overload_penalty = 15.0

        weight = (
            match_score * match_weight
            + skill_count * skill_weight
            + availability * availability_weight
            + (100.0 - workload) * capacity_weight
            + workload_balance_score * workload_balance_weight
            + relative_balance * 0.10
            - overload_penalty
        )

        employees.append({
            "employee": employee,
            "capacity": remaining_capacity,
            "weight": max(weight, 0.01)
        })

    if not employees:
        return [], 0.0, priority_description

    remaining = float(required_allocation)
    allocations = {}
    active = employees.copy()

    # Iteratively distribute allocation. If someone reaches their capacity,
    # remove them and distribute the remainder among the others.
    while remaining > 0.005 and active:

        total_weight = sum(
            item["weight"]
            for item in active
        )

        if total_weight <= 0:
            break

        capped_this_round = []
        allocated_before = sum(allocations.values())

        for item in active:

            employee_id = item["employee"]["id"]

            proposed = (
                remaining
                * item["weight"]
                / total_weight
            )

            current = allocations.get(
                employee_id,
                0.0
            )

            available_for_employee = max(
                0.0,
                item["capacity"] - current
            )

            amount = min(
                proposed,
                available_for_employee
            )

            if amount > 0:
                allocations[employee_id] = round(
                    current + amount,
                    6
                )

            if allocations.get(employee_id, 0.0) >= item["capacity"] - 0.005:
                capped_this_round.append(item)

        allocated_now = sum(allocations.values())
        remaining = max(
            0.0,
            float(required_allocation) - allocated_now
        )

        # Safety against an infinite loop caused by floating point rounding.
        if allocated_now - allocated_before <= 0.000001:
            break

        if not capped_this_round:
            break

        active = [
            item
            for item in active
            if item not in capped_this_round
        ]

    result = []

    for item in employees:

        employee = item["employee"]
        employee_id = employee["id"]

        amount = round(
            allocations.get(employee_id, 0.0),
            2
        )

        if amount > 0:
            result.append({
                "employee": employee,
                "allocation": amount,
                "allocation_weight": round(item["weight"], 2),
                "workload_balance_score": round(
                    100.0 - float(employee["workload"]),
                    2
                )
            })

    # Correct tiny rounding differences so the total is as close as possible
    # to the requested allocation without exceeding it.
    total = round(
        sum(item["allocation"] for item in result),
        2
    )

    if total > required_allocation:
        excess = round(total - required_allocation, 2)

        for item in reversed(result):
            reduction = min(excess, item["allocation"])
            item["allocation"] = round(
                item["allocation"] - reduction,
                2
            )
            excess = round(excess - reduction, 2)
            if excess <= 0:
                break

        result = [
            item for item in result
            if item["allocation"] > 0
        ]

    total = round(
        sum(item["allocation"] for item in result),
        2
    )

    return result, total, priority_description


def calculate_workload_balance(result):
    """Calculate workload metrics after the proposed allocation."""

    if not result:
        return {
            "average": 0.0,
            "highest": 0.0,
            "lowest": 0.0,
            "difference": 0.0,
            "balance_score": 0.0
        }

    final_workloads = []

    for item in result:
        employee = item["employee"]
        final_workloads.append(
            min(
                100.0,
                float(employee["workload"]) + float(item["allocation"])
            )
        )

    average = sum(final_workloads) / len(final_workloads)
    highest = max(final_workloads)
    lowest = min(final_workloads)
    difference = highest - lowest

    # 100 means perfectly balanced; larger spread lowers the score.
    balance_score = max(
        0.0,
        min(100.0, 100.0 - difference)
    )

    return {
        "average": round(average, 2),
        "highest": round(highest, 2),
        "lowest": round(lowest, 2),
        "difference": round(difference, 2),
        "balance_score": round(balance_score, 2)
    }


# ============================================================
# SMART TEAM ALLOCATION
# ============================================================

def calculate_allocation_confidence(employee, allocation):
    """Calculate an explainable confidence score for an employee allocation."""
    match_score = max(0.0, min(100.0, float(employee["score"])))
    availability = max(0.0, min(100.0, float(employee["availability"])))
    workload = max(0.0, min(100.0, float(employee["workload"])))
    capacity_score = max(0.0, min(100.0, (availability + (100.0 - workload)) / 2.0))
    skill_score = max(0.0, min(100.0, float(employee["skill_match"])))
    confidence = (match_score * 0.40 + skill_score * 0.30 + capacity_score * 0.30)
    return round(confidence, 2)


def print_allocation_explanations(allocations):
    """Print human-readable reasons for every recommended allocation."""
    print("\n")
    print("=" * 70)
    print("                 ALLOCATION REASONING")
    print("=" * 70)
    for item in allocations:
        employee = item["employee"]
        allocation = float(item["allocation"])
        current_workload = float(employee["workload"])
        final_workload = min(100.0, current_workload + allocation)
        confidence = calculate_allocation_confidence(employee, allocation)
        print("\n" + employee["name"])
        print("  Allocation Confidence:", confidence, "%")
        print("  Allocation:", round(allocation, 2), "%")
        print("  Workload After Allocation:", round(final_workload, 2), "%")
        print("  Why selected:")
        if employee["matched_skills"]:
            print("   ✓ Covers required skill(s):", ", ".join(sorted(employee["matched_skills"])))
        if float(employee["score"]) >= 60:
            print("   ✓ Strong overall project match")
        elif float(employee["score"]) >= 45:
            print("   ✓ Good overall project match")
        else:
            print("   ✓ Provides useful project skill coverage")
        if float(employee["availability"]) >= 70:
            print("   ✓ High availability")
        elif float(employee["availability"]) >= 50:
            print("   ✓ Sufficient availability")
        else:
            print("   ⚠ Limited availability")
        if current_workload <= 30:
            print("   ✓ Low current workload")
        elif current_workload <= 70:
            print("   ✓ Acceptable current workload")
        else:
            print("   ⚠ High current workload")
        if final_workload <= 70:
            print("   ✓ Remains within a healthy workload range")
        elif final_workload <= 85:
            print("   ⚠ Workload becomes relatively high after allocation")
        else:
            print("   ⚠ Workload is near capacity after allocation")


def calculate_overall_optimization_score(coverage, total_allocation, required_allocation, team_score, balance_score):
    """Combine the main optimization metrics into one explainable score."""
    allocation_fulfillment = 100.0 if required_allocation <= 0 else min(100.0, (float(total_allocation) / float(required_allocation)) * 100.0)
    score = (float(coverage) * 0.35 + allocation_fulfillment * 0.25 + float(balance_score) * 0.20 + float(team_score) * 0.20)
    return round(max(0.0, min(100.0, score)), 2)


def display_allocation_plan(
    project_name,
    priority,
    coverage,
    team_score,
    allocations,
    total_allocation,
    remaining_allocation,
    priority_strategy,
    show_reasoning=True
):
    """Display a complete allocation plan and return its optimization metrics."""

    print("\n")
    print("=" * 70)
    print("             INTELLIGENT ALLOCATION PLAN")
    print("=" * 70)

    print("\nPriority Strategy:", priority_strategy)

    if not allocations:
        print("\n❌ No employees in the selected team have available capacity.")
        return None

    for item in allocations:
        employee = item["employee"]

        print("\n", employee["name"], "→", item["allocation"], "%")
        print(
            "   Matching Skills:",
            ", ".join(sorted(employee["matched_skills"]))
        )
        print("   Match Score:", employee["score"], "%")
        print("   Current Workload:", employee["workload"], "%")
        print("   Available Capacity:", employee["availability"], "%")
        print("   Allocation Weight:", item["allocation_weight"])

    workload_metrics = calculate_workload_balance(allocations)

    print("\n")
    print("=" * 70)
    print("                 WORKLOAD BALANCE ANALYSIS")
    print("=" * 70)

    print(
        "\nAverage Team Workload After Allocation:",
        workload_metrics["average"], "%"
    )
    print(
        "Highest Workload After Allocation:",
        workload_metrics["highest"], "%"
    )
    print(
        "Lowest Workload After Allocation:",
        workload_metrics["lowest"], "%"
    )
    print(
        "Workload Difference:",
        workload_metrics["difference"], "%"
    )
    print(
        "Workload Balance Score:",
        workload_metrics["balance_score"], "%"
    )

    if workload_metrics["highest"] >= 95.0:
        print("\n⚠️ WARNING: At least one selected employee is near full capacity.")
    elif workload_metrics["highest"] >= 85.0:
        print("\n⚠️ Some selected employees have high workload after allocation.")
    elif workload_metrics["difference"] <= 15.0:
        print("\n✅ Team workload is well balanced.")
    elif workload_metrics["difference"] <= 30.0:
        print("\n✅ Team workload is reasonably balanced.")
    else:
        print("\n⚠️ Team workload has a noticeable imbalance.")

    if show_reasoning:
        print_allocation_explanations(allocations)

    allocation_fulfillment = (
        100.0
        if remaining_allocation <= 0
        else min(
            100.0,
            (total_allocation / remaining_allocation) * 100.0
        )
    )

    overall_score = calculate_overall_optimization_score(
        coverage,
        total_allocation,
        remaining_allocation,
        team_score,
        workload_metrics["balance_score"]
    )

    print("\n")
    print("=" * 70)
    print("                    ALLOCATION DECISION SUMMARY")
    print("=" * 70)
    print("\nProject:", project_name)
    print("Priority:", priority)
    print("Team Size:", len(allocations))
    print("Skill Coverage:", round(coverage, 2), "%")
    print("Allocation Fulfilled:", round(allocation_fulfillment, 2), "%")
    print("Workload Balance:", workload_metrics["balance_score"], "%")
    print("Overall Optimization Score:", overall_score, "%")

    print("\nRecommended Team:")
    for item in allocations:
        print("  ✓", item["employee"]["name"], "→", item["allocation"], "%")

    if coverage >= 100.0 and allocation_fulfillment >= 100.0 and overall_score >= 80.0:
        print("\nDecision: ✅ STRONGLY RECOMMENDED")
    elif coverage >= 100.0 and allocation_fulfillment >= 100.0:
        print("\nDecision: ✅ RECOMMENDED")
    elif coverage >= 75.0 and allocation_fulfillment >= 90.0:
        print("\nDecision: ⚠️ ACCEPTABLE WITH LIMITATIONS")
    else:
        print("\nDecision: ⚠️ REVIEW REQUIRED")

    print("\nTotal Allocation:", total_allocation, "%")

    if total_allocation >= remaining_allocation:
        print("Status: ✅ FULLY STAFFABLE")
    else:
        print("Status: ⚠️ PARTIALLY STAFFABLE")
        print(
            "Still Needed:",
            round(remaining_allocation - total_allocation, 2),
            "%"
        )

    return {
        "workload_metrics": workload_metrics,
        "allocation_fulfillment": allocation_fulfillment,
        "overall_score": overall_score
    }


def build_team_allocation_plan(
    project_id,
    remaining_allocation,
    excluded_employee_ids=None
):
    """Build a fresh team and allocation plan using the current database state."""

    excluded_employee_ids = set(excluded_employee_ids or [])

    project = get_project_details(project_id)
    if project is None:
        return None

    project_priority = project[2]
    required_skills = get_project_skills(project_id)

    candidates = get_available_candidates(project_id)

    if excluded_employee_ids:
        candidates = [
            employee
            for employee in candidates
            if employee["id"] not in excluded_employee_ids
        ]

    if not candidates:
        return None

    best_team, coverage, team_score = find_best_team(
        candidates,
        required_skills,
        remaining_allocation
    )

    if best_team is None:
        return None

    allocations, total_allocation, priority_strategy = (
        optimize_team_allocations(
            best_team,
            remaining_allocation,
            project_priority
        )
    )

    if not allocations:
        return None

    return {
        "project": project,
        "project_name": project[1],
        "priority": project_priority,
        "required_skills": required_skills,
        "best_team": best_team,
        "coverage": coverage,
        "team_score": team_score,
        "allocations": allocations,
        "total_allocation": total_allocation,
        "priority_strategy": priority_strategy
    }


def print_team_conflicts(conflicts):
    """Print all V20 pre-flight conflicts in a consistent format."""

    print("\n")
    print("=" * 70)
    print("              TEAM ALLOCATION BLOCKED")
    print("=" * 70)
    print("\n❌ One or more allocation conflicts were detected.")

    for conflict in conflicts:
        if conflict["employee"] is not None:
            print_allocation_conflict(
                conflict["employee"],
                conflict["project"],
                conflict["allocation"],
                conflict["details"]
            )


def conflict_aware_reoptimize(
    project_id,
    remaining_allocation,
    original_allocations,
    max_attempts=3
):
    """
    Version 21 conflict-aware recovery.

    If V20 pre-flight detects a conflict, remove the conflicting employee(s)
    from the candidate pool, rebuild the entire team, recalculate allocations,
    and run the V20 pre-flight again. No database changes are made during this
    process.
    """

    excluded_employee_ids = set()

    for conflict in preflight_team_allocation_conflicts(
        original_allocations,
        project_id
    ):
        employee = conflict.get("employee")
        if employee is not None:
            excluded_employee_ids.add(employee["id"])

    if not excluded_employee_ids:
        return None

    for attempt in range(1, max_attempts + 1):

        print("\n")
        print("=" * 70)
        print("             VERSION 21 RE-OPTIMIZATION")
        print("=" * 70)
        print(
            "\n⚠️ Attempt",
            attempt,
            "of",
            max_attempts,
            "to rebuild the team without conflicting employee(s)."
        )
        print(
            "Excluded Employee ID(s):",
            ", ".join(str(value) for value in sorted(excluded_employee_ids))
        )

        plan = build_team_allocation_plan(
            project_id,
            remaining_allocation,
            excluded_employee_ids
        )

        if plan is None:
            print("\n❌ No feasible replacement team was found.")
            return None

        conflicts = preflight_team_allocation_conflicts(
            plan["allocations"],
            project_id
        )

        if not conflicts:
            print("\n✅ VERSION 21 FOUND A CONFLICT-FREE REPLACEMENT TEAM.")
            return plan

        print("\n⚠️ Replacement plan still has conflicts.")
        print_team_conflicts(conflicts)

        new_conflicts = set()
        for conflict in conflicts:
            employee = conflict.get("employee")
            if employee is not None:
                new_conflicts.add(employee["id"])

        before = len(excluded_employee_ids)
        excluded_employee_ids.update(new_conflicts)

        if len(excluded_employee_ids) == before:
            return None

    print("\n❌ VERSION 21 could not produce a conflict-free team.")
    return None


def smart_team_allocation():

    print("\n")
    print("=" * 70)
    print("             SKILL-COVERAGE SMART TEAM BUILDER")
    print("=" * 70)

    try:
        project_id = int(input("\nEnter Project ID: "))
    except ValueError:
        print("\nPlease enter a valid Project ID.")
        return

    project = get_project_details(project_id)

    if project is None:
        print("\n❌ Project not found.")
        return

    project_name = project[1]
    priority = project[2]
    required_allocation = float(project[3])
    required_skills = get_project_skills(project_id)

    print("\nProject:", project_name)
    print("Priority:", priority)
    print("Required Allocation:", required_allocation, "%")
    print("Required Skills:", ", ".join(required_skills))

    if not required_skills:
        print("\n❌ Project has no required skills.")
        return

    current_allocation = get_current_project_allocation(project_id)
    remaining_allocation = required_allocation - current_allocation

    print("\nAlready Allocated:", current_allocation, "%")
    print("Allocation Still Needed:", remaining_allocation, "%")

    if remaining_allocation <= 0:
        print("\n✅ Project is already fully staffed.")
        return

    candidates = get_available_candidates(project_id)

    if not candidates:
        print("\n❌ No employees have matching skills.")
        return

    print("\n")
    print("=" * 70)
    print("                 AVAILABLE CANDIDATES")
    print("=" * 70)

    for employee in candidates:
        print("\n" + employee["name"])
        print("  Skills:", ", ".join(employee["skills"]))
        print(
            "  Matching Skills:",
            ", ".join(employee["matched_skills"])
        )
        print("  Skill Match:", round(employee["skill_match"], 2), "%")
        print("  Availability:", employee["availability"], "%")
        print("  Workload:", employee["workload"], "%")
        print("  Experience:", employee["experience"], "years")
        print("  Score:", employee["score"], "%")

    plan = build_team_allocation_plan(
        project_id,
        remaining_allocation
    )

    if plan is None:
        print("\n❌ Could not create a team.")
        return

    best_team = plan["best_team"]
    coverage = plan["coverage"]
    team_score = plan["team_score"]
    allocations = plan["allocations"]
    total_allocation = plan["total_allocation"]
    priority_strategy = plan["priority_strategy"]

    print("\n")
    print("=" * 70)
    print("                    OPTIMAL TEAM")
    print("=" * 70)

    covered_skills = set()
    for employee in best_team:
        covered_skills.update(employee["matched_skills"])

    uncovered_skills = set(required_skills) - covered_skills

    print("\nTeam Size:", len(best_team))
    print("Skill Coverage:", round(coverage, 2), "%")
    print("Team Score:", round(team_score, 2), "%")
    print("\nSelected Employees:")

    for index, employee in enumerate(best_team, start=1):
        print("\n", index, ".", employee["name"])
        print("   Skills:", ", ".join(employee["skills"]))
        print(
            "   Project Skills Covered:",
            ", ".join(employee["matched_skills"])
        )
        print("   Match Score:", employee["score"], "%")
        print("   Availability:", employee["availability"], "%")
        print("   Workload:", employee["workload"], "%")
        print("   Experience:", employee["experience"], "years")

    print("\n")
    print("=" * 70)
    print("                    SKILL ANALYSIS")
    print("=" * 70)
    print("\nRequired Skills:", ", ".join(required_skills))
    print("Covered Skills:", ", ".join(sorted(covered_skills)))

    if uncovered_skills:
        print("Uncovered Skills:", ", ".join(sorted(uncovered_skills)))
        print("\n⚠️ Team does not cover every required skill.")
    else:
        print("Uncovered Skills: None")
        print("\n✅ ALL REQUIRED SKILLS ARE COVERED")

    metrics = display_allocation_plan(
        project_name,
        priority,
        coverage,
        team_score,
        allocations,
        total_allocation,
        remaining_allocation,
        priority_strategy,
        show_reasoning=True
    )

    if metrics is None:
        return

    confirmation = input(
        "\nApply this optimized team allocation? (Y/N): "
    )

    if confirmation.lower() != "y":
        print("\nAllocation cancelled.")
        return

    # --------------------------------------------------------
    # VERSION 20 - CONFLICT PRE-FLIGHT
    # --------------------------------------------------------
    # The entire proposed team is validated before any INSERT occurs.
    conflicts = preflight_team_allocation_conflicts(
        allocations,
        project_id
    )

    # --------------------------------------------------------
    # VERSION 21 - CONFLICT-AWARE RE-OPTIMIZATION
    # --------------------------------------------------------
    # Instead of stopping immediately, V21 attempts to replace the
    # conflicting employee(s) and rebuild the complete team.
    if conflicts:

        print_team_conflicts(conflicts)

        print("\n")
        print("=" * 70)
        print("        VERSION 21: SMART CONFLICT RECOVERY")
        print("=" * 70)
        print(
            "\nThe original team is blocked, but the database has NOT been changed."
        )
        print(
            "Version 21 will now search for replacement employee(s) and "
            "re-optimize the entire team."
        )

        replacement_plan = conflict_aware_reoptimize(
            project_id,
            remaining_allocation,
            allocations,
            max_attempts=3
        )

        if replacement_plan is None:
            print("\n❌ No safe replacement plan is available.")
            print("No database changes were made.")
            return

        replacement_allocations = replacement_plan["allocations"]
        replacement_coverage = replacement_plan["coverage"]
        replacement_team_score = replacement_plan["team_score"]
        replacement_total = replacement_plan["total_allocation"]
        replacement_strategy = replacement_plan["priority_strategy"]

        print("\n")
        print("=" * 70)
        print("             REVISED VERSION 21 TEAM")
        print("=" * 70)

        for item in replacement_allocations:
            print(
                "\n  ✓",
                item["employee"]["name"],
                "→",
                item["allocation"],
                "%"
            )

        display_allocation_plan(
            project_name,
            priority,
            replacement_coverage,
            replacement_team_score,
            replacement_allocations,
            replacement_total,
            remaining_allocation,
            replacement_strategy,
            show_reasoning=True
        )

        print("\n")
        print("=" * 70)
        print("                 V21 REVISED PLAN VALIDATION")
        print("=" * 70)

        replacement_conflicts = preflight_team_allocation_conflicts(
            replacement_allocations,
            project_id
        )

        if replacement_conflicts:
            print_team_conflicts(replacement_conflicts)
            print("\n❌ Revised plan failed final validation.")
            print("No database changes were made.")
            return

        print("\n✅ Revised team passed the V20 pre-flight safety check.")

        confirmation = input(
            "\nApply the revised Version 21 team allocation? (Y/N): "
        )

        if confirmation.lower() != "y":
            print("\nRevised allocation cancelled.")
            return

        # The replacement plan becomes the final plan used below.
        allocations = replacement_allocations
        total_allocation = replacement_total
        coverage = replacement_coverage

    # --------------------------------------------------------
    # FINAL SAFETY CHECK
    # --------------------------------------------------------
    # Always run V20 pre-flight immediately before database changes.
    final_conflicts = preflight_team_allocation_conflicts(
        allocations,
        project_id
    )

    if final_conflicts:
        print_team_conflicts(final_conflicts)
        print("\n❌ FINAL SAFETY CHECK FAILED.")
        print("No database changes were made.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        for item in allocations:
            employee = item["employee"]
            employee_id = employee["id"]
            allocation = float(item["allocation"])

            cursor.execute("""
                SELECT
                    availability,
                    workload
                FROM employees
                WHERE employee_id = %s;
            """, (employee_id,))

            data = cursor.fetchone()

            if data is None:
                raise Exception("Employee no longer exists.")

            availability = float(data[0])
            workload = float(data[1])

            if allocation > availability:
                raise Exception("Employee does not have enough availability.")

            if workload + allocation > 100:
                raise Exception("Employee workload would exceed 100%.")

            cursor.execute("""
                SELECT
                    COALESCE(SUM(allocation_percentage), 0)
                FROM allocations
                WHERE employee_id = %s
                AND project_id = %s;
            """, (employee_id, project_id))

            existing_project_allocation = float(cursor.fetchone()[0])

            if existing_project_allocation > 0:
                raise Exception(
                    "Employee is already allocated to this project."
                )

            cursor.execute("""
                INSERT INTO allocations
                (
                    employee_id,
                    project_id,
                    allocation_percentage
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                );
            """, (employee_id, project_id, allocation))

            cursor.execute("""
                UPDATE employees
                SET
                    availability = availability - %s,
                    workload = workload + %s
                WHERE employee_id = %s;
            """, (allocation, allocation, employee_id))

            log_allocation_history(
                connection,
                employee_id,
                project_id,
                "ADD",
                0.0,
                allocation
            )

        connection.commit()

        print("\n")
        print("=" * 70)
        print("             TEAM ALLOCATION SUCCESSFUL")
        print("=" * 70)
        print("\nProject:", project_name)
        print("Employees Added:", len(allocations))
        print("Allocation Added:", total_allocation, "%")
        print("Skill Coverage:", round(coverage, 2), "%")
        print("\nDatabase successfully updated.")

    except Exception as error:
        connection.rollback()
        print("\n❌ TEAM ALLOCATION FAILED")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()


# ============================================================
# ADD EMPLOYEE
# ============================================================

def add_employee():

    print("\n")
    print("=" * 70)
    print("                       ADD EMPLOYEE")
    print("=" * 70)

    name = input(
        "\nEnter employee name: "
    ).strip()

    if not name:

        print(
            "\n❌ Name cannot be empty."
        )

        return

    try:

        experience = float(
            input(
                "Enter experience in years: "
            )
        )

        availability = float(
            input(
                "Enter availability percentage: "
            )
        )

        workload = float(
            input(
                "Enter current workload percentage: "
            )
        )

    except ValueError:

        print(
            "\n❌ Please enter valid numbers."
        )

        return

    if experience < 0:

        print(
            "\n❌ Experience cannot be negative."
        )

        return

    if availability < 0 or availability > 100:

        print(
            "\n❌ Availability must be between 0 and 100."
        )

        return

    if workload < 0 or workload > 100:

        print(
            "\n❌ Workload must be between 0 and 100."
        )

        return

    if workload + availability > 100:

        print(
            "\n❌ Workload + availability cannot exceed 100."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO employees
            (
                name,
                experience,
                availability,
                workload
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )

            RETURNING employee_id;
        """, (
            name,
            experience,
            availability,
            workload
        ))

        employee_id = cursor.fetchone()[0]

        connection.commit()

        print(
            "\n✅ Employee added successfully."
        )

        print(
            "Employee ID:",
            employee_id
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Could not add employee."
        )

        print(
            "Reason:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ADD SKILL
# ============================================================

def add_skill():

    print("\n")
    print("=" * 70)
    print("                         ADD SKILL")
    print("=" * 70)

    skill_name = input(
        "\nEnter skill name: "
    ).strip()

    if not skill_name:

        print(
            "\n❌ Skill name cannot be empty."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                skill_id

            FROM skills

            WHERE LOWER(skill_name)
                = LOWER(%s);
        """, (
            skill_name,
        ))

        existing = cursor.fetchone()

        if existing:

            print(
                "\n❌ Skill already exists."
            )

            print(
                "Existing Skill ID:",
                existing[0]
            )

            cursor.close()
            connection.close()

            return

        cursor.execute("""
            INSERT INTO skills
            (
                skill_name
            )

            VALUES
            (
                %s
            )

            RETURNING skill_id;
        """, (
            skill_name,
        ))

        skill_id = cursor.fetchone()[0]

        connection.commit()

        print(
            "\n✅ Skill added successfully."
        )

        print(
            "Skill ID:",
            skill_id
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Could not add skill."
        )

        print(
            "Reason:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ADD PROJECT
# ============================================================

def add_project():

    print("\n")
    print("=" * 70)
    print("                       ADD PROJECT")
    print("=" * 70)

    name = input(
        "\nEnter project name: "
    ).strip()

    if not name:

        print(
            "\n❌ Project name cannot be empty."
        )

        return

    priority = input(
        "Enter priority (High/Medium/Low): "
    ).strip().capitalize()

    if priority not in [
        "High",
        "Medium",
        "Low"
    ]:

        print(
            "\n❌ Priority must be High, Medium or Low."
        )

        return

    try:

        required_allocation = float(
            input(
                "Enter required allocation percentage: "
            )
        )

    except ValueError:

        print(
            "\n❌ Invalid allocation."
        )

        return

    if (
        required_allocation <= 0
        or
        required_allocation > 100
    ):

        print(
            "\n❌ Allocation must be between 1 and 100."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO projects
            (
                name,
                priority,
                required_allocation
            )

            VALUES
            (
                %s,
                %s,
                %s
            )

            RETURNING project_id;
        """, (
            name,
            priority,
            required_allocation
        ))

        project_id = cursor.fetchone()[0]

        connection.commit()

        print(
            "\n✅ Project added successfully."
        )

        print(
            "Project ID:",
            project_id
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Could not add project."
        )

        print(
            "Reason:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ASSIGN SKILL TO EMPLOYEE
# ============================================================

def assign_skill_to_employee():

    print("\n")
    print("=" * 70)
    print("                 ASSIGN SKILL TO EMPLOYEE")
    print("=" * 70)

    view_employees()
    view_skills()

    try:

        employee_id = int(
            input(
                "\nEnter Employee ID: "
            )
        )

        skill_id = int(
            input(
                "Enter Skill ID: "
            )
        )

    except ValueError:

        print(
            "\n❌ IDs must be numbers."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT employee_id
            FROM employees
            WHERE employee_id = %s;
        """, (
            employee_id,
        ))

        if cursor.fetchone() is None:

            print(
                "\n❌ Employee not found."
            )

            return

        cursor.execute("""
            SELECT skill_id
            FROM skills
            WHERE skill_id = %s;
        """, (
            skill_id,
        ))

        if cursor.fetchone() is None:

            print(
                "\n❌ Skill not found."
            )

            return

        cursor.execute("""
            SELECT
                employee_id,
                skill_id

            FROM employee_skills

            WHERE employee_id = %s
            AND skill_id = %s;
        """, (
            employee_id,
            skill_id
        ))

        if cursor.fetchone():

            print(
                "\n❌ Employee already has this skill."
            )

            return

        cursor.execute("""
            INSERT INTO employee_skills
            (
                employee_id,
                skill_id
            )

            VALUES
            (
                %s,
                %s
            );
        """, (
            employee_id,
            skill_id
        ))

        connection.commit()

        print(
            "\n✅ Skill assigned successfully."
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Could not assign skill."
        )

        print(
            "Reason:",
            error
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ASSIGN SKILL TO PROJECT
# ============================================================

def assign_skill_to_project():

    print("\n")
    print("=" * 70)
    print("                  ASSIGN SKILL TO PROJECT")
    print("=" * 70)

    view_projects()
    view_skills()

    try:

        project_id = int(
            input(
                "\nEnter Project ID: "
            )
        )

        skill_id = int(
            input(
                "Enter Skill ID: "
            )
        )

    except ValueError:

        print(
            "\n❌ IDs must be numbers."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT project_id
            FROM projects
            WHERE project_id = %s;
        """, (
            project_id,
        ))

        if cursor.fetchone() is None:

            print(
                "\n❌ Project not found."
            )

            return

        cursor.execute("""
            SELECT skill_id
            FROM skills
            WHERE skill_id = %s;
        """, (
            skill_id,
        ))

        if cursor.fetchone() is None:

            print(
                "\n❌ Skill not found."
            )

            return

        cursor.execute("""
            SELECT
                project_id,
                skill_id

            FROM project_skills

            WHERE project_id = %s
            AND skill_id = %s;
        """, (
            project_id,
            skill_id
        ))

        if cursor.fetchone():

            print(
                "\n❌ Project already requires this skill."
            )

            return

        cursor.execute("""
            INSERT INTO project_skills
            (
                project_id,
                skill_id
            )

            VALUES
            (
                %s,
                %s
            );
        """, (
            project_id,
            skill_id
        ))

        connection.commit()

        print(
            "\n✅ Skill assigned to project successfully."
        )

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Could not assign skill."
        )

        print(
            "Reason:",
            error
        )

    finally:

        cursor.close()
        connection.close()



# ============================================================
# VERSION 22 - SMART PROJECT REBALANCING + VERSION 23 AUDIT LOGGING
# ============================================================

def smart_rebalance_project():
    """
    VERSION 22 - Smart Project Rebalancing + Allocation Gap Filling.

    Handles:
      * Under-allocated projects: finds suitable employees for the gap.
      * Fully/over-allocated projects: proposes a balanced team.
      * Safety checks before any database write.
      * Atomic database transaction on confirmation.
    """

    print("\n")
    print("=" * 70)
    print("          VERSION 22 SMART REBALANCING + GAP FILLING")
    print("=" * 70)

    try:
        project_id = int(input("\nEnter Project ID: "))
    except ValueError:
        print("\n❌ Please enter a valid Project ID.")
        return

    project = get_project_details(project_id)

    if project is None:
        print("\n❌ Project not found.")
        return

    project_name = project[1]
    priority = project[2]
    required_allocation = float(project[3])

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                a.allocation_id,
                a.employee_id,
                e.name,
                a.allocation_percentage,
                e.availability,
                e.workload,
                e.experience
            FROM allocations a
            JOIN employees e
                ON a.employee_id = e.employee_id
            WHERE a.project_id = %s
            ORDER BY a.allocation_percentage DESC, e.name;
        """, (project_id,))

        rows = cursor.fetchall()

    except Exception as error:
        print("\n❌ Could not read project allocations.")
        print("Reason:", error)
        return

    finally:
        cursor.close()
        connection.close()

    current_allocations = []

    for row in rows:
        current_allocations.append({
            "allocation_id": row[0],
            "employee_id": row[1],
            "name": row[2],
            "allocation": float(row[3]),
            "availability": float(row[4]),
            "workload": float(row[5]),
            "experience": row[6]
        })

    current_total = sum(
        item["allocation"] for item in current_allocations
    )

    gap = required_allocation - current_total

    print("\nProject:", project_name)
    print("Priority:", priority)
    print("Required Allocation:", required_allocation, "%")
    print("Current Allocation:", round(current_total, 2), "%")

    print("\n")
    print("=" * 70)
    print("                  CURRENT PROJECT TEAM")
    print("=" * 70)

    if current_allocations:
        for item in current_allocations:
            print("\n", item["name"])
            print("  Allocation:", item["allocation"], "%")
            print("  Availability:", item["availability"], "%")
            print("  Workload:", item["workload"], "%")
            print("  Experience:", item["experience"], "years")
    else:
        print("\nNo employees are currently allocated.")

    # ========================================================
    # CASE 1: UNDER-ALLOCATED PROJECT
    # ========================================================

    if gap > 0.01:
        print("\n")
        print("=" * 70)
        print("                 ALLOCATION GAP DETECTED")
        print("=" * 70)
        print("\nMissing Allocation:", round(gap, 2), "%")

        # Ask the existing recommendation engine for suitable candidates.
        try:
            recommendations = recommend_employees(project_id)
        except TypeError:
            recommendations = None
        except Exception:
            recommendations = None

        # The recommendation function in this project is primarily
        # presentation-oriented, so we independently obtain candidates
        # from the database for a reliable allocation plan.
        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT
                    e.employee_id,
                    e.name,
                    e.availability,
                    e.workload,
                    e.experience
                FROM employees e
                WHERE e.availability >= %s
                AND e.employee_id NOT IN (
                    SELECT employee_id
                    FROM allocations
                    WHERE project_id = %s
                )
                ORDER BY e.workload ASC,
                         e.experience DESC,
                         e.employee_id;
            """, (gap, project_id))

            candidate_rows = cursor.fetchall()

            # Get required project skills.
            cursor.execute("""
                SELECT skill_id
                FROM project_skills
                WHERE project_id = %s;
            """, (project_id,))
            required_skill_ids = {
                row[0] for row in cursor.fetchall()
            }

            candidates = []

            for row in candidate_rows:
                employee_id = row[0]

                cursor.execute("""
                    SELECT skill_id
                    FROM employee_skills
                    WHERE employee_id = %s;
                """, (employee_id,))

                employee_skill_ids = {
                    skill_row[0]
                    for skill_row in cursor.fetchall()
                }

                matched = len(
                    required_skill_ids & employee_skill_ids
                )

                coverage = (
                    matched / len(required_skill_ids) * 100
                    if required_skill_ids else 100.0
                )

                candidates.append({
                    "employee_id": employee_id,
                    "name": row[1],
                    "availability": float(row[2]),
                    "workload": float(row[3]),
                    "experience": row[4],
                    "coverage": coverage,
                    "matched_skills": matched
                })

        except Exception as error:
            print("\n❌ Could not generate gap-filling candidates.")
            print("Reason:", error)
            return

        finally:
            cursor.close()
            connection.close()

        if not candidates:
            print("\n❌ No available employee can safely fill the gap.")
            print("No database changes were made.")
            return

        # Rank by skill coverage first, then lower workload, then experience.
        candidates.sort(
            key=lambda c: (
                -c["coverage"],
                c["workload"],
                -float(c["experience"] or 0),
                c["employee_id"]
            )
        )

        selected = candidates[0]
        proposed_allocation = round(
            min(gap, selected["availability"]),
            2
        )

        if proposed_allocation <= 0:
            print("\n❌ No usable allocation capacity was found.")
            return

        print("\n")
        print("=" * 70)
        print("                SMART GAP-FILL RECOMMENDATION")
        print("=" * 70)

        print("\nRecommended Employee:", selected["name"])
        print("Employee ID:", selected["employee_id"])
        print("Allocation:", proposed_allocation, "%")
        print("Availability:", selected["availability"], "%")
        print("Current Workload:", selected["workload"], "%")
        print("Skill Coverage:", round(selected["coverage"], 2), "%")
        print("Matched Project Skills:", selected["matched_skills"])

        if proposed_allocation < gap - 0.01:
            print(
                "\n⚠️ This employee can fill only",
                proposed_allocation,
                "% of the",
                round(gap, 2),
                "% gap."
            )

        confirmation = input(
            "\nApply this smart gap-fill? (Y/N): "
        )

        if confirmation.lower() != "y":
            print("\nGap filling cancelled.")
            return

        connection = get_connection()
        cursor = connection.cursor()

        try:
            # Re-check state inside the transaction immediately before write.
            cursor.execute("""
                SELECT availability, workload
                FROM employees
                WHERE employee_id = %s
                FOR UPDATE;
            """, (selected["employee_id"],))

            state = cursor.fetchone()

            if state is None:
                raise Exception("Employee no longer exists.")

            availability = float(state[0])
            workload = float(state[1])

            if proposed_allocation > availability + 0.01:
                raise Exception(
                    "Employee availability changed; allocation is no longer safe."
                )

            if workload + proposed_allocation > 100.01:
                raise Exception(
                    "Employee workload would exceed 100%."
                )

            # Confirm the employee is still not allocated to the project.
            cursor.execute("""
                SELECT 1
                FROM allocations
                WHERE employee_id = %s
                AND project_id = %s;
            """, (selected["employee_id"], project_id))

            if cursor.fetchone() is not None:
                raise Exception(
                    "Employee is already allocated to this project."
                )

            cursor.execute("""
                INSERT INTO allocations
                (
                    employee_id,
                    project_id,
                    allocation_percentage
                )
                VALUES (%s, %s, %s);
            """, (
                selected["employee_id"],
                project_id,
                proposed_allocation
            ))

            cursor.execute("""
                UPDATE employees
                SET
                    availability = availability - %s,
                    workload = workload + %s
                WHERE employee_id = %s;
            """, (
                proposed_allocation,
                proposed_allocation,
                selected["employee_id"]
            ))

            log_allocation_history(
                connection,
                selected["employee_id"],
                project_id,
                "ADD",
                0.0,
                proposed_allocation
            )

            connection.commit()

            print("\n")
            print("=" * 70)
            print("                 SMART GAP-FILL SUCCESSFUL")
            print("=" * 70)
            print("\nProject:", p.name)
            print("Employee:", selected["name"])
            print("Allocation Added:", proposed_allocation, "%")
            print(
                "Project Allocation Now:",
                round(current_total + proposed_allocation, 2),
                "%"
            )
            print("\n✅ Database successfully updated.")

        except Exception as error:
            connection.rollback()
            print("\n❌ Smart gap-fill failed.")
            print("Reason:", error)
            print("No partial database changes were committed.")

        finally:
            cursor.close()
            connection.close()

        return

    # ========================================================
    # CASE 2: FULLY ALLOCATED / OVER-ALLOCATED PROJECT
    # ========================================================

    print("\n")
    print("=" * 70)
    print("                 REBALANCING ANALYSIS")
    print("=" * 70)

    try:
        plan = build_team_allocation_plan(
            project_id,
            required_allocation
        )
    except Exception as error:
        print("\n❌ Could not generate a rebalancing plan.")
        print("Reason:", error)
        return

    if plan is None:
        print("\n❌ No feasible rebalanced team could be generated.")
        return

    proposed_allocations = plan["allocations"]
    proposed_total = float(plan["total_allocation"])
    proposed_coverage = float(plan["coverage"])
    proposed_team_score = float(plan["team_score"])
    proposed_strategy = plan["priority_strategy"]

    proposed_by_employee = {
        item["employee"]["id"]: item
        for item in proposed_allocations
    }

    current_by_employee = {
        item["employee_id"]: item
        for item in current_allocations
    }

    changed = []

    for employee_id, item in proposed_by_employee.items():
        old = current_by_employee.get(employee_id)

        if old is None:
            changed.append({
                "type": "ADD",
                "employee_id": employee_id,
                "name": item["employee"]["name"],
                "old": 0.0,
                "new": float(item["allocation"])
            })
        else:
            old_value = float(old["allocation"])
            new_value = float(item["allocation"])

            if abs(old_value - new_value) > 0.01:
                changed.append({
                    "type": "CHANGE",
                    "employee_id": employee_id,
                    "name": item["employee"]["name"],
                    "old": old_value,
                    "new": new_value
                })

    for employee_id, old in current_by_employee.items():
        if employee_id not in proposed_by_employee:
            changed.append({
                "type": "REMOVE",
                "employee_id": employee_id,
                "name": old["name"],
                "old": float(old["allocation"]),
                "new": 0.0
            })

    if not changed:
        print("\n✅ NO REBALANCING NEEDED")
        print("The current project team already matches the optimizer.")
        return

    print("\n")
    print("=" * 70)
    print("                    REBALANCING PLAN")
    print("=" * 70)

    for change in changed:
        if change["type"] == "ADD":
            print(
                "\n  +",
                change["name"],
                ": 0.0 % →",
                round(change["new"], 2),
                "%"
            )
        elif change["type"] == "REMOVE":
            print(
                "\n  -",
                change["name"],
                ":",
                round(change["old"], 2),
                "% → 0.0 %"
            )
        else:
            direction = "↑" if change["new"] > change["old"] else "↓"
            print(
                "\n  ",
                direction,
                change["name"],
                ":",
                round(change["old"], 2),
                "% →",
                round(change["new"], 2),
                "%"
            )

    print("\nProposed Total Allocation:", round(proposed_total, 2), "%")
    print("Proposed Skill Coverage:", round(proposed_coverage, 2), "%")
    print("Proposed Team Score:", round(proposed_team_score, 2), "%")
    print("Priority Strategy:", proposed_strategy)

    # Safety validation before write.
    conflicts = preflight_team_allocation_conflicts(
        proposed_allocations,
        project_id
    )

    if conflicts:
        print("\n❌ REBALANCING BLOCKED")
        print_team_conflicts(conflicts)
        print("\nNo database changes were made.")
        return

    print("\n✅ Proposed team passed the safety check.")

    confirmation = input(
        "\nApply this Version 22 rebalancing? (Y/N): "
    )

    if confirmation.lower() != "y":
        print("\nRebalancing cancelled.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Lock affected employee rows for the duration of the transaction.
        affected_ids = set(current_by_employee.keys())
        affected_ids.update(proposed_by_employee.keys())

        for employee_id in affected_ids:
            cursor.execute("""
                SELECT employee_id
                FROM employees
                WHERE employee_id = %s
                FOR UPDATE;
            """, (employee_id,))

        # Remove employees no longer in the proposed team.
        for change in changed:
            if change["type"] == "REMOVE":
                cursor.execute("""
                    DELETE FROM allocations
                    WHERE employee_id = %s
                    AND project_id = %s;
                """, (
                    change["employee_id"],
                    project_id
                ))

                cursor.execute("""
                    UPDATE employees
                    SET
                        availability = availability + %s,
                        workload = workload - %s
                    WHERE employee_id = %s;
                """, (
                    change["old"],
                    change["old"],
                    change["employee_id"]
                ))

                log_allocation_history(
                    connection,
                    change["employee_id"],
                    project_id,
                    "REMOVE",
                    change["old"],
                    0.0
                )

        # Update existing allocations and add new allocations.
        for item in proposed_allocations:
            employee_id = item["employee"]["id"]
            new_allocation = float(item["allocation"])
            old = current_by_employee.get(employee_id)

            if old is not None:
                old_allocation = float(old["allocation"])
                delta = new_allocation - old_allocation

                if abs(delta) <= 0.01:
                    continue

                if delta > 0:
                    cursor.execute("""
                        SELECT availability, workload
                        FROM employees
                        WHERE employee_id = %s;
                    """, (employee_id,))

                    state = cursor.fetchone()

                    if state is None:
                        raise Exception(
                            "Employee no longer exists."
                        )

                    if float(state[0]) + 0.01 < delta:
                        raise Exception(
                            "Employee does not have enough availability."
                        )

                    if float(state[1]) + delta > 100.01:
                        raise Exception(
                            "Employee workload would exceed 100%."
                        )

                cursor.execute("""
                    UPDATE allocations
                    SET allocation_percentage = %s
                    WHERE employee_id = %s
                    AND project_id = %s;
                """, (
                    new_allocation,
                    employee_id,
                    project_id
                ))

                cursor.execute("""
                    UPDATE employees
                    SET
                        availability = availability - %s,
                        workload = workload + %s
                    WHERE employee_id = %s;
                """, (
                    delta,
                    delta,
                    employee_id
                ))

                log_allocation_history(
                    connection,
                    employee_id,
                    project_id,
                    "MODIFY",
                    old_allocation,
                    new_allocation
                )

            else:
                cursor.execute("""
                    SELECT availability, workload
                    FROM employees
                    WHERE employee_id = %s;
                """, (employee_id,))

                state = cursor.fetchone()

                if state is None:
                    raise Exception("Employee no longer exists.")

                availability = float(state[0])
                workload = float(state[1])

                if new_allocation > availability + 0.01:
                    raise Exception(
                        "Employee does not have enough availability."
                    )

                if workload + new_allocation > 100.01:
                    raise Exception(
                        "Employee workload would exceed 100%."
                    )

                cursor.execute("""
                    INSERT INTO allocations
                    (
                        employee_id,
                        project_id,
                        allocation_percentage
                    )
                    VALUES (%s, %s, %s);
                """, (
                    employee_id,
                    project_id,
                    new_allocation
                ))

                cursor.execute("""
                    UPDATE employees
                    SET
                        availability = availability - %s,
                        workload = workload + %s
                    WHERE employee_id = %s;
                """, (
                    new_allocation,
                    new_allocation,
                    employee_id
                ))

                log_allocation_history(
                    connection,
                    employee_id,
                    project_id,
                    "ADD",
                    0.0,
                    new_allocation
                )

        connection.commit()

        print("\n")
        print("=" * 70)
        print("             SMART REBALANCING SUCCESSFUL")
        print("=" * 70)
        print("\nProject:", project_name)
        print("Previous Allocation:", round(current_total, 2), "%")
        print("New Allocation:", round(proposed_total, 2), "%")
        print("Skill Coverage:", round(proposed_coverage, 2), "%")
        print("Employees Changed:", len(changed))
        print("\n✅ Database successfully updated.")

    except Exception as error:
        connection.rollback()

        print("\n❌ SMART REBALANCING FAILED")
        print("Reason:", error)
        print("No partial database changes were committed.")

    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERSION 23 - VIEW ALLOCATION HISTORY
# ============================================================

def view_allocation_history():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                h.history_id,
                e.name,
                p.name,
                h.action,
                h.old_allocation,
                h.new_allocation,
                h.changed_at
            FROM allocation_history h
            JOIN employees e
                ON h.employee_id = e.employee_id
            JOIN projects p
                ON h.project_id = p.project_id
            ORDER BY h.history_id DESC;
        """)

        history = cursor.fetchall()

        print("\n")
        print("=" * 70)
        print("                 ALLOCATION AUDIT HISTORY")
        print("=" * 70)

        if not history:
            print("\nNo allocation history found.")
            return

        for record in history:
            print("\nHistory ID:", record[0])
            print("Employee:", record[1])
            print("Project:", record[2])
            print("Action:", record[3])
            print("Old Allocation:", record[4], "%")
            print("New Allocation:", record[5], "%")
            print("Changed At:", record[6])
            print("-" * 70)

    except Exception as error:
        print("\n❌ Could not read allocation history.")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERSION 26 - RESOURCE ALLOCATION PERFORMANCE ANALYTICS
# ============================================================

def resource_allocation_performance():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(AVG(workload), 0),
                COALESCE(MAX(workload), 0),
                COUNT(*) FILTER (WHERE workload < 50),
                COUNT(*) FILTER (WHERE workload > 90)
            FROM employees;
        """)

        employee_stats = cursor.fetchone()
        total_employees = employee_stats[0]
        average_workload = float(employee_stats[1] or 0)
        highest_workload = float(employee_stats[2] or 0)
        underutilized_employees = employee_stats[3]
        overloaded_employees = employee_stats[4]

        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE current_allocation >= required_allocation),
                COUNT(*) FILTER (WHERE current_allocation < required_allocation),
                COUNT(*) FILTER (WHERE current_allocation > required_allocation)
            FROM (
                SELECT
                    p.project_id,
                    p.required_allocation,
                    COALESCE(SUM(a.allocation_percentage), 0) AS current_allocation
                FROM projects p
                LEFT JOIN allocations a
                    ON p.project_id = a.project_id
                GROUP BY p.project_id, p.required_allocation
            ) project_data;
        """)

        project_stats = cursor.fetchone()
        total_projects = project_stats[0]
        fully_staffed_projects = project_stats[1]
        understaffed_projects = project_stats[2]
        overstaffed_projects = project_stats[3]

        cursor.execute("SELECT COUNT(*) FROM allocations;")
        total_active_allocations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                p.name,
                p.required_allocation,
                COALESCE(SUM(a.allocation_percentage), 0) AS current_allocation
            FROM projects p
            LEFT JOIN allocations a
                ON p.project_id = a.project_id
            GROUP BY p.project_id, p.name, p.required_allocation
            ORDER BY p.project_id;
        """)

        project_data = cursor.fetchall()
        project_scores = []

        for project_name, required, current in project_data:
            required = float(required or 0)
            current = float(current or 0)

            if required > 0:
                staffing_percentage = min((current / required) * 100, 100)
            else:
                staffing_percentage = 100

            project_scores.append(staffing_percentage)

        project_staffing_score = (
            sum(project_scores) / len(project_scores)
            if project_scores else 100
        )

        if total_employees == 0:
            resource_balance_score = 100
        else:
            overload_penalty = (overloaded_employees / total_employees) * 100
            underutilization_penalty = (underutilized_employees / total_employees) * 50
            resource_balance_score = max(
                0,
                100 - overload_penalty - underutilization_penalty
            )

        overall_health_score = (
            project_staffing_score * 0.60
            + resource_balance_score * 0.40
        )

        if overall_health_score >= 80:
            health_status = "EXCELLENT"
            recommendation = "Resource allocation is well balanced. Maintain current strategy."
        elif overall_health_score >= 60:
            health_status = "GOOD"
            recommendation = "Minor resource adjustments may improve overall allocation efficiency."
        elif overall_health_score >= 40:
            health_status = "NEEDS ATTENTION"
            recommendation = "Resource redistribution is recommended to improve project staffing and workload balance."
        else:
            health_status = "CRITICAL"
            recommendation = "Immediate resource reallocation is recommended."

        print("\n")
        print("=" * 70)
        print("          RESOURCE ALLOCATION PERFORMANCE ANALYTICS")
        print("=" * 70)

        print("\nORGANIZATION SUMMARY")
        print("-" * 70)
        print("Total Employees          :", total_employees)
        print("Total Projects           :", total_projects)
        print("Total Active Allocations :", total_active_allocations)

        print("\nPROJECT PERFORMANCE")
        print("-" * 70)

        if not project_data:
            print("No projects found.")
        else:
            for project_name, required, current in project_data:
                required = float(required or 0)
                current = float(current or 0)

                if required > 0:
                    staffing_percentage = min((current / required) * 100, 100)
                else:
                    staffing_percentage = 100

                if current > required:
                    status = "OVERSTAFFED"
                elif current >= required:
                    status = "FULLY STAFFED"
                elif current > 0:
                    status = "UNDERSTAFFED"
                else:
                    status = "UNSTAFFED"

                print(
                    f"{project_name:<25} "
                    f"{staffing_percentage:>6.2f}% | "
                    f"{status}"
                )

        print("\nRESOURCE UTILIZATION")
        print("-" * 70)
        print(f"Average Employee Load    : {average_workload:.2f}%")
        print(f"Highest Employee Load    : {highest_workload:.2f}%")
        print(f"Underutilized Employees  : {underutilized_employees}")
        print(f"Overloaded Employees     : {overloaded_employees}")

        print("\nALLOCATION HEALTH")
        print("-" * 70)
        print(f"Fully Staffed Projects   : {fully_staffed_projects}")
        print(f"Understaffed Projects    : {understaffed_projects}")
        print(f"Overstaffed Projects     : {overstaffed_projects}")
        print(f"\nProject Staffing Score   : {project_staffing_score:.2f} / 100")
        print(f"Resource Balance Score   : {resource_balance_score:.2f} / 100")
        print(f"Overall Resource Health  : {overall_health_score:.2f} / 100")
        print(f"Health Status            : {health_status}")
        print(f"Recommendation           : {recommendation}")
        print("\n" + "=" * 70)

    except Exception as error:
        print("\n❌ RESOURCE PERFORMANCE ANALYTICS FAILED")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERSION 25 - RESOURCE DEMAND FORECAST
# ============================================================

def resource_demand_forecast():

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                p.project_id,
                p.name,
                p.priority,
                p.required_allocation,
                COALESCE(SUM(a.allocation_percentage), 0)
            FROM projects p
            LEFT JOIN allocations a
                ON p.project_id = a.project_id
            GROUP BY
                p.project_id,
                p.name,
                p.priority,
                p.required_allocation
            ORDER BY p.project_id;
        """)

        projects = cursor.fetchall()

        print("\\n" + "=" * 70)
        print("              RESOURCE DEMAND FORECAST")
        print("=" * 70)

        if not projects:
            print("\\nNo projects found.")
            return

        for project_id, project_name, priority, required, current in projects:

            required = float(required or 0)
            current = float(current or 0)
            gap = max(required - current, 0)
            excess = max(current - required, 0)

            # Demand score combines allocation gap and project priority.
            priority_text = str(priority or "Medium").strip().lower()
            priority_weight = {
                "low": 0.75,
                "medium": 1.0,
                "high": 1.25,
                "critical": 1.5
            }.get(priority_text, 1.0)

            if required > 0:
                gap_percent = (gap / required) * 100
            else:
                gap_percent = 0

            demand_score = min(100, gap_percent * priority_weight)

            if gap <= 0:
                if excess > 0:
                    status = "OVER-SUPPLIED"
                    forecast = "RESOURCE SURPLUS"
                    action = "Review excess allocation or rebalance resources"
                else:
                    status = "STABLE"
                    forecast = "NO SHORTAGE EXPECTED"
                    action = "Maintain current allocation"
            elif demand_score >= 75:
                status = "CRITICAL DEMAND"
                forecast = "SEVERE RESOURCE SHORTAGE"
                action = "Immediate resource allocation required"
            elif demand_score >= 40:
                status = "HIGH DEMAND"
                forecast = "RESOURCE SHORTAGE LIKELY"
                action = "Allocate additional resources soon"
            else:
                status = "MODERATE DEMAND"
                forecast = "POTENTIAL SHORTAGE"
                action = "Monitor capacity and plan additional resources"

            print("\\n" + "-" * 70)
            print(f"Project: {project_name}")
            print(f"Priority: {priority}")
            print(f"Current Allocation : {current:.2f}%")
            print(f"Required Allocation: {required:.2f}%")
            print(f"Allocation Gap     : {gap:.2f}%")
            print(f"Demand Score       : {demand_score:.2f} / 100")
            print(f"Demand Status      : {status}")
            print(f"Forecast           : {forecast}")
            print(f"Recommended Action : {action}")

        print("\\n" + "=" * 70)

    except Exception as error:
        print("\\n❌ Error generating demand forecast")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERSION 28 - INTELLIGENT RESOURCE ALLOCATION ADVISOR
# ============================================================

def intelligent_resource_allocation_advisor():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # --------------------------------------------------------
        # PROJECT RESOURCE DEMAND
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                p.project_id,
                p.name,
                p.priority,
                p.required_allocation,
                COALESCE(SUM(a.allocation_percentage), 0)
            FROM projects p
            LEFT JOIN allocations a
                ON p.project_id = a.project_id
            GROUP BY
                p.project_id,
                p.name,
                p.priority,
                p.required_allocation
            ORDER BY p.project_id;
        """)
        projects = cursor.fetchall()

        # --------------------------------------------------------
        # EMPLOYEE CAPACITY
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                employee_id,
                name,
                availability,
                workload
            FROM employees
            ORDER BY employee_id;
        """)
        employees = cursor.fetchall()

        # --------------------------------------------------------
        # HISTORICAL ACTIVITY
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE UPPER(action) = 'ADD'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'MODIFY'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'REMOVE')
            FROM allocation_history;
        """)
        history = cursor.fetchone()

        total_history = history[0] or 0
        add_history = history[1] or 0
        modify_history = history[2] or 0
        remove_history = history[3] or 0

        # --------------------------------------------------------
        # CALCULATE CURRENT HEALTH
        # --------------------------------------------------------
        staffing_scores = []
        understaffed_projects = []
        fully_staffed_projects = []
        excess_projects = []

        for project_id, name, priority, required, current in projects:
            required = float(required or 0)
            current = float(current or 0)

            staffing_score = (
                min((current / required) * 100, 100)
                if required > 0 else 100
            )
            staffing_scores.append(staffing_score)

            if current < required:
                gap = required - current
                understaffed_projects.append({
                    "id": project_id,
                    "name": name,
                    "priority": str(priority or "Medium"),
                    "required": required,
                    "current": current,
                    "gap": gap
                })
            elif current > required:
                excess_projects.append({
                    "id": project_id,
                    "name": name,
                    "priority": str(priority or "Medium"),
                    "required": required,
                    "current": current,
                    "excess": current - required
                })
            else:
                fully_staffed_projects.append(name)

        project_staffing_score = (
            sum(staffing_scores) / len(staffing_scores)
            if staffing_scores else 100
        )

        underutilized = 0
        overloaded = 0
        available_employees = []

        for employee_id, name, availability, workload in employees:
            availability = float(availability or 0)
            workload = float(workload or 0)

            if workload < 50:
                underutilized += 1

            if workload > 90:
                overloaded += 1

            safe_capacity = min(
                availability,
                max(0.0, 100.0 - workload)
            )

            if safe_capacity >= 10:
                available_employees.append({
                    "id": employee_id,
                    "name": name,
                    "availability": availability,
                    "workload": workload,
                    "capacity": safe_capacity
                })

        total_employees = len(employees)

        resource_balance_score = (
            max(
                0,
                100
                - (overloaded / total_employees) * 100
                - (underutilized / total_employees) * 50
            )
            if total_employees > 0 else 100
        )

        health_score = (
            project_staffing_score * 0.60
            + resource_balance_score * 0.40
        )

        # --------------------------------------------------------
        # RANK PROJECTS FOR ACTION
        # --------------------------------------------------------
        priority_weights = {
            "low": 0.75,
            "medium": 1.0,
            "high": 1.25,
            "critical": 1.50
        }

        for project in understaffed_projects:
            priority_key = project["priority"].strip().lower()
            weight = priority_weights.get(priority_key, 1.0)
            project["demand_score"] = min(
                100,
                (project["gap"] / project["required"] * 100)
                * weight
            ) if project["required"] > 0 else 0

        understaffed_projects.sort(
            key=lambda x: x["demand_score"],
            reverse=True
        )

        # --------------------------------------------------------
        # GENERATE ACTIONS
        # --------------------------------------------------------
        actions = []

        for project in understaffed_projects[:5]:
            if project["demand_score"] >= 75:
                severity = "CRITICAL"
            elif project["demand_score"] >= 40:
                severity = "HIGH"
            else:
                severity = "MODERATE"

            actions.append({
                "severity": severity,
                "project": project["name"],
                "message": (
                    f"Allocate approximately {project['gap']:.2f}% "
                    f"additional capacity to this project."
                )
            })

        # Excess allocation can be a source of reusable capacity.
        for project in excess_projects[:3]:
            actions.append({
                "severity": "OPTIMIZE",
                "project": project["name"],
                "message": (
                    f"Review {project['excess']:.2f}% excess allocation "
                    "for possible reassignment."
                )
            })

        # --------------------------------------------------------
        # SYSTEM RECOMMENDATION
        # --------------------------------------------------------
        if not projects:
            overall_recommendation = (
                "No projects are currently available for resource advice."
            )
        elif health_score < 40:
            overall_recommendation = (
                "Immediate resource reallocation is required. "
                "Prioritize critical project shortages first."
            )
        elif health_score < 60:
            overall_recommendation = (
                "Resource allocation needs attention. "
                "Redistribute available capacity toward understaffed projects."
            )
        elif health_score < 80:
            overall_recommendation = (
                "Resource allocation is acceptable but can be improved "
                "through targeted redistribution."
            )
        else:
            overall_recommendation = (
                "Resource allocation is healthy. Maintain the current "
                "strategy and monitor demand trends."
            )

        if not employees:
            capacity_recommendation = "No employees are available for reassignment analysis."
        elif available_employees and understaffed_projects:
            capacity_recommendation = (
                f"{len(available_employees)} employee(s) have at least "
                "10% safe capacity and may be considered for reassignment."
            )
        elif understaffed_projects:
            capacity_recommendation = (
                "Understaffed projects exist, but no employee currently "
                "has enough safe capacity for a straightforward reassignment."
            )
        else:
            capacity_recommendation = (
                "No project staffing shortage currently requires reassignment."
            )

        # --------------------------------------------------------
        # DISPLAY ADVISOR
        # --------------------------------------------------------
        print("\n")
        print("=" * 70)
        print("             INTELLIGENT RESOURCE ALLOCATION ADVISOR")
        print("=" * 70)

        print("\nSYSTEM HEALTH")
        print("-" * 70)
        print(f"Resource Health Score : {health_score:.2f} / 100")

        if health_score >= 80:
            status = "EXCELLENT"
        elif health_score >= 60:
            status = "GOOD"
        elif health_score >= 40:
            status = "NEEDS IMPROVEMENT"
        else:
            status = "CRITICAL"

        print(f"Overall Status        : {status}")
        print(f"Project Staffing Score : {project_staffing_score:.2f} / 100")
        print(f"Resource Balance Score : {resource_balance_score:.2f} / 100")

        print("\nPRIORITY ACTIONS")
        print("-" * 70)

        if not actions:
            print("No immediate allocation actions detected.")
        else:
            for index, action in enumerate(actions, start=1):
                print(f"\n{index}. [{action['severity']}] {action['project']}")
                print(f"   → {action['message']}")

        print("\nCURRENT PROJECT STATUS")
        print("-" * 70)

        if not projects:
            print("No projects found.")
        else:
            for project_id, name, priority, required, current in projects:
                required = float(required or 0)
                current = float(current or 0)
                gap = max(required - current, 0)
                staffing = (
                    min((current / required) * 100, 100)
                    if required > 0 else 100
                )

                if current >= required:
                    project_status = "FULLY STAFFED"
                elif current > 0:
                    project_status = "UNDERSTAFFED"
                else:
                    project_status = "UNSTAFFED"

                print(
                    f"{name:<25} {staffing:>6.2f}% | "
                    f"{project_status:<14} | Gap: {gap:.2f}%"
                )

        print("\nRESOURCE CAPACITY")
        print("-" * 70)
        print(f"Total Employees       : {total_employees}")
        print(f"Employees With Capacity: {len(available_employees)}")
        print(f"Underutilized         : {underutilized}")
        print(f"Overloaded            : {overloaded}")
        print(f"Fully Staffed Projects: {len(fully_staffed_projects)}")
        print(f"Understaffed Projects : {len(understaffed_projects)}")
        print(f"Excess-Allocated Projects: {len(excess_projects)}")
        print(f"\nCapacity Insight      : {capacity_recommendation}")

        print("\nHISTORICAL SIGNAL")
        print("-" * 70)
        print(f"Allocation Changes    : {total_history}")
        print(f"ADD Changes           : {add_history}")
        print(f"MODIFY Changes        : {modify_history}")
        print(f"REMOVE Changes        : {remove_history}")

        if total_history == 0:
            historical_signal = "No historical allocation activity is available yet."
        elif remove_history > add_history:
            historical_signal = (
                "Resource reductions currently exceed additions; review "
                "projects experiencing declining allocation."
            )
        elif add_history > remove_history:
            historical_signal = (
                "Resource additions exceed removals; monitor whether "
                "resource concentration is increasing."
            )
        else:
            historical_signal = (
                "Historical additions and removals are relatively balanced."
            )

        print(f"Historical Insight   : {historical_signal}")

        print("\nFINAL ADVISORY")
        print("-" * 70)
        print(f"Recommendation       : {overall_recommendation}")

        if understaffed_projects:
            top = understaffed_projects[0]
            print(
                f"Top Priority Project : {top['name']} "
                f"({top['priority']} priority, "
                f"{top['gap']:.2f}% gap)"
            )
        else:
            print("Top Priority Project : None")

        print("\n" + "=" * 70)

    except Exception as error:
        print("\n❌ INTELLIGENT ADVISOR FAILED")
        print("Reason:", error)
    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERSION 27 - ALLOCATION TREND & HISTORICAL INTELLIGENCE
# ============================================================

def allocation_trend_analytics():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE UPPER(action) = 'ADD'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'MODIFY'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'REMOVE')
            FROM allocation_history;
        """)
        summary = cursor.fetchone()
        total_changes = summary[0] or 0
        add_changes = summary[1] or 0
        modify_changes = summary[2] or 0
        remove_changes = summary[3] or 0

        cursor.execute("""
            SELECT p.name, COUNT(*) AS change_count
            FROM allocation_history h
            JOIN projects p ON h.project_id = p.project_id
            GROUP BY p.project_id, p.name
            ORDER BY change_count DESC, p.project_id
            LIMIT 1;
        """)
        active_project = cursor.fetchone()

        cursor.execute("""
            SELECT e.name, COUNT(*) AS change_count
            FROM allocation_history h
            JOIN employees e ON h.employee_id = e.employee_id
            GROUP BY e.employee_id, e.name
            ORDER BY change_count DESC, e.employee_id
            LIMIT 1;
        """)
        active_employee = cursor.fetchone()

        cursor.execute("""
            SELECT
                p.name,
                COALESCE(SUM(COALESCE(h.new_allocation, 0) - COALESCE(h.old_allocation, 0)), 0),
                COUNT(*)
            FROM allocation_history h
            JOIN projects p ON h.project_id = p.project_id
            GROUP BY p.project_id, p.name
            ORDER BY p.project_id;
        """)
        project_trends = cursor.fetchall()

        cursor.execute("""
            SELECT p.name, p.required_allocation,
                   COALESCE(SUM(a.allocation_percentage), 0)
            FROM projects p
            LEFT JOIN allocations a ON p.project_id = a.project_id
            GROUP BY p.project_id, p.name, p.required_allocation
            ORDER BY p.project_id;
        """)
        current_projects = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE workload < 50),
                   COUNT(*) FILTER (WHERE workload > 90)
            FROM employees;
        """)
        employee_stats = cursor.fetchone()
        total_employees = employee_stats[0] or 0
        underutilized = employee_stats[1] or 0
        overloaded = employee_stats[2] or 0

        staffing_scores = []
        for project_name, required, current in current_projects:
            required = float(required or 0)
            current = float(current or 0)
            staffing_scores.append(min((current / required) * 100, 100) if required > 0 else 100)

        project_staffing_score = sum(staffing_scores) / len(staffing_scores) if staffing_scores else 100
        resource_balance_score = (
            max(0, 100 - (overloaded / total_employees) * 100 - (underutilized / total_employees) * 50)
            if total_employees > 0 else 100
        )
        current_health = project_staffing_score * 0.60 + resource_balance_score * 0.40

        if total_changes == 0:
            activity_status = "NO HISTORICAL ACTIVITY"
        elif total_changes <= 5:
            activity_status = "LOW ACTIVITY"
        elif total_changes <= 15:
            activity_status = "MODERATE ACTIVITY"
        else:
            activity_status = "HIGH ACTIVITY"

        print("\n")
        print("=" * 70)
        print("          ALLOCATION TREND & HISTORICAL INTELLIGENCE")
        print("=" * 70)

        print("\nALLOCATION HISTORY SUMMARY")
        print("-" * 70)
        print(f"Total Allocation Changes : {total_changes}")
        print(f"New Allocations          : {add_changes}")
        print(f"Modified Allocations     : {modify_changes}")
        print(f"Removed Allocations      : {remove_changes}")
        print(f"Historical Activity      : {activity_status}")

        print("\nMOST ACTIVE ENTITIES")
        print("-" * 70)
        print(f"Most Active Project      : {active_project[0]} ({active_project[1]} changes)" if active_project else "Most Active Project      : No history available")
        print(f"Most Active Employee     : {active_employee[0]} ({active_employee[1]} changes)" if active_employee else "Most Active Employee     : No history available")

        print("\nPROJECT ALLOCATION TRENDS")
        print("-" * 70)
        if not project_trends:
            print("No allocation history available for trend analysis.")
        else:
            for project_name, net_change, change_count in project_trends:
                net_change = float(net_change or 0)
                trend = "INCREASING" if net_change > 0.01 else "DECREASING" if net_change < -0.01 else "STABLE"
                print(f"{project_name:<25} Net Change: {net_change:>7.2f}% | {trend:<10} | Changes: {change_count}")

        print("\nCURRENT PROJECT STAFFING")
        print("-" * 70)
        if not current_projects:
            print("No projects found.")
        else:
            for project_name, required, current in current_projects:
                required = float(required or 0)
                current = float(current or 0)
                staffing_percentage = min((current / required) * 100, 100) if required > 0 else 100
                status = "FULLY STAFFED" if current >= required else "UNDERSTAFFED" if current > 0 else "UNSTAFFED"
                print(f"{project_name:<25} {staffing_percentage:>6.2f}% | {status}")

        print("\nRESOURCE HEALTH SNAPSHOT")
        print("-" * 70)
        print(f"Current Resource Health  : {current_health:.2f} / 100")
        if current_health >= 80:
            health_message = "Resource allocation is healthy and well balanced."
        elif current_health >= 60:
            health_message = "Resource allocation is generally healthy but can be improved."
        elif current_health >= 40:
            health_message = "Resource allocation needs attention and redistribution."
        else:
            health_message = "Resource allocation is critical and requires immediate action."
        print(f"Health Insight            : {health_message}")

        print("\nHISTORICAL INSIGHTS")
        print("-" * 70)
        decreasing_projects = [name for name, net, count in project_trends if float(net or 0) < -0.01]
        increasing_projects = [name for name, net, count in project_trends if float(net or 0) > 0.01]
        if decreasing_projects:
            print("⚠ Projects with decreasing allocation: " + ", ".join(decreasing_projects))
        if increasing_projects:
            print("↑ Projects with increasing allocation: " + ", ".join(increasing_projects))
        if not decreasing_projects and not increasing_projects:
            print("→ No significant historical allocation movement detected.")

        if not project_trends:
            recommendation = "Start recording allocation changes to build historical intelligence."
        elif decreasing_projects:
            recommendation = "Review decreasing-allocation projects and prioritize them if their current staffing remains below requirements."
        elif increasing_projects:
            recommendation = "Monitor projects with increasing allocation to prevent future resource concentration."
        else:
            recommendation = "Allocation levels are relatively stable; continue monitoring project demand and employee workload."
        print(f"Recommendation           : {recommendation}")
        print("\n" + "=" * 70)

    except Exception as error:
        print("\n❌ ERROR GENERATING HISTORICAL ANALYTICS")
        print("Reason:", error)
    finally:
        cursor.close()
        connection.close()


# ============================================================
# MAIN MENU
# ============================================================

def main():

    try:

        initialize_database()

    except Exception as error:

        print("\n❌ DATABASE ERROR")
        print("Reason:", error)

        return

    while True:

        print("\n\n")

        print("=" * 70)
        print("          SMART RESOURCE ALLOCATION PLATFORM")
        print("                    VERSION 32")
        print("=" * 70)

        print("1.  View Employees")
        print("2.  View Skills")
        print("3.  View Projects")
        print("4.  Test Employee-Project Match")
        print("5.  Recommend Employees")
        print("6.  Allocate Employee to Project")
        print("7.  Remove Allocation")
        print("8.  View Current Allocations")
        print("9.  Project Allocation Dashboard")
        print("10. Skill-Coverage Smart Team Allocation")
        print("11. Exit")

        print("\n--------------- DATA MANAGEMENT ---------------")

        print("12. Add Employee")
        print("13. Add Skill")
        print("14. Add Project")
        print("15. Assign Skill to Employee")
        print("16. Assign Skill to Project")
        print("17. Modify Existing Allocation")
        print("18. Smart Rebalance Project")
        print("19. View Allocation History")
        print("20. Resource Utilization Analytics")
        print("21. Project Risk Analysis")
        print("22. Resource Demand Forecast")
        print("23. Resource Allocation Performance Analytics")
        print("24. Allocation Trend & Historical Intelligence")
        print("25. Intelligent Resource Allocation Advisor")
        print("26. Smart Resource Reallocation Engine")
        print("27. Allocation Optimization Engine")
        print("28. Executive Resource Dashboard & KPIs")
        print("29. System Validation & Integrity Check")

        choice = input(
            "\nEnter your choice: "
        )

        if choice == "1":

            view_employees()

        elif choice == "2":

            view_skills()

        elif choice == "3":

            view_projects()

        elif choice == "4":

            test_matching()

        elif choice == "5":

            recommend_employees()

        elif choice == "6":

            allocate_employee()

        elif choice == "7":

            remove_allocation()

        elif choice == "8":

            view_allocations()

        elif choice == "9":

            project_allocation_dashboard()

        elif choice == "10":

            smart_team_allocation()

        elif choice == "11":

            print(
                "\nThank you for using "
                "Smart Resource Allocation Platform."
            )

            print("Goodbye!")

            break

        elif choice == "12":

            add_employee()

        elif choice == "13":

            add_skill()

        elif choice == "14":

            add_project()

        elif choice == "15":

            assign_skill_to_employee()

        elif choice == "16":

            assign_skill_to_project()

        elif choice == "17":

            modify_allocation()

        elif choice == "18":

            smart_rebalance_project()

        elif choice == "19":

            view_allocation_history()

        elif choice == "20":

            resource_utilization_analytics()

        elif choice == "21":

            project_risk_analysis()

        elif choice == "22":

            resource_demand_forecast()

        elif choice == "23":

            resource_allocation_performance()

        elif choice == "24":

            allocation_trend_analytics()

        elif choice == "25":

            intelligent_resource_allocation_advisor()

        elif choice == "26":

            smart_resource_reallocation_engine()

        elif choice == "27":

            allocation_optimization_engine()

        elif choice == "28":

            executive_resource_dashboard()

        elif choice == "29":

            system_validation_integrity_check()

        else:

            print(
                "\n❌ Invalid choice."
            )

            print(
                "Please enter a number from 1 to 29."
            )


# ============================================================
# VERSION 30 - SMART RESOURCE REALLOCATION ENGINE
# ============================================================

def smart_resource_reallocation_engine():
    """Rank safe employee candidates for an understaffed project.
    Advisory only: this version does not change the database.
    """
    print("\n")
    print("=" * 70)
    print("              SMART RESOURCE REALLOCATION ENGINE")
    print("=" * 70)

    try:
        project_id = int(input("\nEnter Project ID: "))
    except ValueError:
        print("\n❌ Please enter a valid Project ID.")
        return

    project = get_project_details(project_id)
    if project is None:
        print("\n❌ Project not found.")
        return

    project_name = project[1]
    priority = str(project[2])
    required = float(project[3] or 0)
    project_skills = get_project_skills(project_id)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT employee_id,
                   COALESCE(SUM(allocation_percentage), 0)
            FROM allocations
            WHERE project_id = %s
            GROUP BY employee_id;
        """, (project_id,))
        project_rows = cursor.fetchall()

        cursor.execute("""
            SELECT employee_id, name, experience, availability, workload
            FROM employees
            ORDER BY employee_id;
        """)
        employees = cursor.fetchall()
    except Exception as error:
        print("\n❌ Could not calculate reallocation candidates.")
        print("Reason:", error)
        return
    finally:
        cursor.close()
        connection.close()

    current = sum(float(row[1] or 0) for row in project_rows)
    gap = max(required - current, 0.0)

    print("\nProject:", project_name)
    print("Priority:", priority)
    print("Required Allocation:", round(required, 2), "%")
    print("Current Allocation:", round(current, 2), "%")
    print("Allocation Gap:", round(gap, 2), "%")
    print("Required Skills:", ", ".join(project_skills) if project_skills else "None specified")

    if gap <= 0.01:
        print("\n✅ This project does not currently have an allocation gap.")
        print("No reallocation is required.")
        print("=" * 70)
        return

    allocated_ids = {row[0] for row in project_rows}
    candidates = []

    for employee in employees:
        employee_id, name, experience, availability, workload = employee
        if employee_id in allocated_ids:
            continue

        experience = float(experience or 0)
        availability = float(availability or 0)
        workload = float(workload or 0)
        safe_capacity = max(0.0, min(availability, 100.0 - workload))
        if safe_capacity < 1.0:
            continue

        skills = get_employee_skills(employee_id)
        skill_match = calculate_skill_match(skills, project_skills)
        workload_score = max(0.0, 100.0 - workload)
        experience_score = min((experience / 10.0) * 100.0, 100.0)

        score = (
            skill_match * 0.50
            + safe_capacity * 0.30
            + workload_score * 0.10
            + experience_score * 0.10
        )

        if skill_match >= 75 and safe_capacity >= 20:
            recommendation = "STRONG CANDIDATE"
        elif skill_match >= 50 and safe_capacity >= 10:
            recommendation = "GOOD CANDIDATE"
        else:
            recommendation = "LIMITED CANDIDATE"

        candidates.append({
            "id": employee_id,
            "name": name,
            "experience": experience,
            "availability": availability,
            "workload": workload,
            "safe_capacity": safe_capacity,
            "skill_match": skill_match,
            "score": round(score, 2),
            "recommendation": recommendation
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    print("\n")
    print("=" * 70)
    print("                    CANDIDATE RESOURCES")
    print("=" * 70)

    if not candidates:
        print("\n❌ No employees currently have safe available capacity.")
        print("Recommendation: Rebalance another project or increase capacity first.")
        print("\n" + "=" * 70)
        return

    for rank, candidate in enumerate(candidates, 1):
        print(f"\n{rank}. {candidate['name']}")
        print("   Employee ID     :", candidate["id"])
        print("   Current Workload:", round(candidate["workload"], 2), "%")
        print("   Availability    :", round(candidate["availability"], 2), "%")
        print("   Safe Capacity   :", round(candidate["safe_capacity"], 2), "%")
        print("   Skill Match     :", round(candidate["skill_match"], 2), "%")
        print("   Candidate Score :", candidate["score"], "/ 100")
        print("   Recommendation  :", candidate["recommendation"])

    remaining = gap
    plan = []
    for candidate in candidates:
        if remaining <= 0.01:
            break
        suggested = min(remaining, candidate["safe_capacity"], 20.0)
        if suggested > 0:
            plan.append((candidate, round(suggested, 2)))
            remaining -= suggested

    print("\n")
    print("=" * 70)
    print("                 OPTIMAL REALLOCATION PLAN")
    print("=" * 70)

    proposed = 0.0
    for candidate, amount in plan:
        proposed += amount
        print(f"\n→ {candidate['name']} (ID {candidate['id']})")
        print("  Suggested Allocation:", amount, "%")
        print("  Candidate Score:", candidate["score"], "/ 100")

    projected = current + proposed
    print("\nProposed Additional Allocation:", round(proposed, 2), "%")
    print("Projected Project Allocation :", round(projected, 2), "%")
    print("Remaining Gap                :", round(max(gap - proposed, 0), 2), "%")
    print("Plan Status                  :", "GAP CAN BE FULLY COVERED" if remaining <= 0.01 else "PARTIAL GAP COVERAGE")

    if priority.lower() == "high":
        confidence = 95.0 if remaining <= 0.01 else 80.0
    elif priority.lower() == "medium":
        confidence = 90.0 if remaining <= 0.01 else 75.0
    else:
        confidence = 85.0 if remaining <= 0.01 else 70.0

    print("\nAllocation Confidence:", confidence, "/ 100")
    print("Recommendation       :", "Execute the proposed redistribution after reviewing candidate skills." if remaining <= 0.01 else "Use the proposed candidates, but additional capacity is still required.")
    print("\n⚠️ Advisory only: no database allocation was changed by Version 29.")
    print("=" * 70)


# ============================================================
# VERSION 30 - ALLOCATION OPTIMIZATION ENGINE
# ============================================================

def allocation_optimization_engine():
    """Find a best-fit allocation plan for an understaffed project.
    Advisory only: this version does not change the database.
    The optimizer uses 5% allocation increments and balances skill,
    safe capacity, workload, experience, project priority, and the
    number of employees used in the plan.
    """
    print("\n")
    print("=" * 70)
    print("                ALLOCATION OPTIMIZATION ENGINE")
    print("=" * 70)

    try:
        project_id = int(input("\nEnter Project ID: "))
    except ValueError:
        print("\n❌ Please enter a valid Project ID.")
        return

    project = get_project_details(project_id)
    if project is None:
        print("\n❌ Project not found.")
        return

    project_name = project[1]
    priority = str(project[2])
    required = float(project[3] or 0)
    project_skills = get_project_skills(project_id)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT employee_id,
                   COALESCE(SUM(allocation_percentage), 0)
            FROM allocations
            WHERE project_id = %s
            GROUP BY employee_id;
        """, (project_id,))
        project_rows = cursor.fetchall()

        cursor.execute("""
            SELECT employee_id, name, experience, availability, workload
            FROM employees
            ORDER BY employee_id;
        """)
        employee_rows = cursor.fetchall()
    except Exception as error:
        print("\n❌ Could not run allocation optimization.")
        print("Reason:", error)
        return
    finally:
        cursor.close()
        connection.close()

    allocated_ids = {row[0] for row in project_rows}
    current_allocation = sum(float(row[1] or 0) for row in project_rows)
    gap = max(required - current_allocation, 0.0)

    print("\nProject:", project_name)
    print("Priority:", priority)
    print("Required Allocation:", round(required, 2), "%")
    print("Current Allocation:", round(current_allocation, 2), "%")
    print("Allocation Gap:", round(gap, 2), "%")
    print("Required Skills:", ", ".join(project_skills) if project_skills else "None specified")

    if gap <= 0.01:
        print("\n✅ This project is already fully staffed.")
        print("No additional optimization is required.")
        print("=" * 70)
        return

    # --------------------------------------------------------
    # BUILD CANDIDATES
    # --------------------------------------------------------
    candidates = []

    for employee_id, name, experience, availability, workload in employee_rows:
        if employee_id in allocated_ids:
            continue

        experience = float(experience or 0)
        availability = max(0.0, min(float(availability or 0), 100.0))
        workload = max(0.0, min(float(workload or 0), 100.0))
        safe_capacity = max(0.0, min(availability, 100.0 - workload))

        if safe_capacity < 5.0:
            continue

        skills = get_employee_skills(employee_id)
        skill_match = float(calculate_skill_match(skills, project_skills))
        workload_score = max(0.0, 100.0 - workload)
        capacity_score = min(safe_capacity, 100.0)
        experience_score = min((experience / 10.0) * 100.0, 100.0)

        # Skill is deliberately the strongest factor.
        # Capacity and workload prevent unsafe recommendations.
        base_score = (
            skill_match * 0.55
            + capacity_score * 0.25
            + workload_score * 0.10
            + experience_score * 0.10
        )

        # High-priority projects slightly favor stronger candidates.
        priority_bonus = {
            "high": 3.0,
            "medium": 1.5,
            "low": 0.0
        }.get(priority.lower(), 0.0)

        optimization_score = min(100.0, base_score + priority_bonus)

        candidates.append({
            "id": employee_id,
            "name": name,
            "experience": experience,
            "availability": availability,
            "workload": workload,
            "safe_capacity": safe_capacity,
            "skill_match": skill_match,
            "score": round(optimization_score, 2),
            "skills": skills
        })

    if not candidates:
        print("\n❌ No employees have enough safe capacity for optimization.")
        print("Recommendation: Increase capacity or rebalance another project first.")
        print("=" * 70)
        return

    # --------------------------------------------------------
    # FILTER FOR SKILL-AWARE OPTIMIZATION
    # --------------------------------------------------------
    skill_qualified = [c for c in candidates if c["skill_match"] >= 50.0]

    if skill_qualified:
        optimization_pool = skill_qualified
        skill_rule = "Candidates with at least 50% required-skill coverage were prioritized."
    else:
        optimization_pool = candidates
        skill_rule = "No candidate covers at least 50% of required skills; best available capacity was used."

    optimization_pool.sort(key=lambda c: c["score"], reverse=True)

    print("\n")
    print("=" * 70)
    print("                    OPTIMIZATION CRITERIA")
    print("=" * 70)
    print("Skill Weight            : 55%")
    print("Safe Capacity Weight    : 25%")
    print("Workload Weight         : 10%")
    print("Experience Weight       : 10%")
    print("Allocation Increment    : 5%")
    print("Skill Rule              :", skill_rule)

    # --------------------------------------------------------
    # DYNAMIC PROGRAMMING OPTIMIZER
    # --------------------------------------------------------
    # Convert the gap/capacities to 5% units. A plan never assigns
    # more than safe capacity and never exceeds the project gap.
    gap_units = max(0, int(round(gap / 5.0)))
    if gap_units == 0:
        gap_units = 1

    dp = {0: (0.0, [])}

    for candidate in optimization_pool:
        capacity_units = int(candidate["safe_capacity"] // 5)
        if capacity_units <= 0:
            continue

        next_dp = dict(dp)

        for used_units, (value, selected) in dp.items():
            # Never allow a transition to exceed the exact project gap.
            # This prevents the optimizer from proposing more allocation
            # than the project actually requires.
            remaining_units = gap_units - used_units
            if remaining_units <= 0:
                continue

            max_add_units = min(capacity_units, remaining_units)

            for add_units in range(1, max_add_units + 1):
                new_units = used_units + add_units

                # Candidate value rewards skill/capacity quality while
                # applying a small penalty to unnecessary fragmentation.
                allocation = add_units * 5
                contribution = candidate["score"] * allocation / 100.0
                employee_penalty = 1.5 if candidate not in selected else 0.0
                new_value = value + contribution - employee_penalty

                old = next_dp.get(new_units)
                if old is None or new_value > old[0]:
                    new_selected = list(selected)
                    existing = next(
                        (item for item in new_selected if item["candidate"]["id"] == candidate["id"]),
                        None
                    )
                    if existing:
                        existing["units"] += add_units
                    else:
                        new_selected.append({"candidate": candidate, "units": add_units})
                    next_dp[new_units] = (new_value, new_selected)

        dp = next_dp

    best = dp.get(gap_units)

    if best is None:
        # Fall back to a safe greedy plan when the exact gap cannot be
        # represented with available 5% capacity increments.
        selected_plan = []
        remaining = gap
        for candidate in optimization_pool:
            allocation = min(remaining, (candidate["safe_capacity"] // 5) * 5)
            if allocation >= 5:
                selected_plan.append({
                    "candidate": candidate,
                    "units": int(allocation // 5)
                })
                remaining -= allocation
                if remaining < 5:
                    break
    else:
        selected_plan = best[1]

    proposed = sum(item["units"] * 5 for item in selected_plan)
    remaining_gap = max(gap - proposed, 0.0)

    # --------------------------------------------------------
    # CONFIDENCE / SAFETY CHECK
    # --------------------------------------------------------
    if selected_plan:
        weighted_score = sum(
            item["candidate"]["score"] * item["units"]
            for item in selected_plan
        ) / sum(item["units"] for item in selected_plan)
        weighted_skill = sum(
            item["candidate"]["skill_match"] * item["units"]
            for item in selected_plan
        ) / sum(item["units"] for item in selected_plan)
    else:
        weighted_score = 0.0
        weighted_skill = 0.0

    coverage_factor = 100.0 if remaining_gap < 0.01 else max(
        0.0, (proposed / gap) * 100.0
    )
    confidence = (
        weighted_score * 0.55
        + weighted_skill * 0.25
        + coverage_factor * 0.20
    )
    confidence = round(min(100.0, confidence), 2)

    # --------------------------------------------------------
    # DISPLAY PLAN
    # --------------------------------------------------------
    print("\n")
    print("=" * 70)
    print("                 OPTIMAL ALLOCATION PLAN")
    print("=" * 70)

    if not selected_plan:
        print("\n❌ No safe allocation plan could be generated.")
    else:
        for rank, item in enumerate(selected_plan, 1):
            candidate = item["candidate"]
            allocation = item["units"] * 5
            print(f"\n{rank}. {candidate['name']} (ID {candidate['id']})")
            print("   Suggested Allocation :", f"{allocation:.2f}%")
            print("   Skill Match          :", f"{candidate['skill_match']:.2f}%")
            print("   Safe Capacity        :", f"{candidate['safe_capacity']:.2f}%")
            print("   Current Workload     :", f"{candidate['workload']:.2f}%")
            print("   Optimization Score   :", f"{candidate['score']:.2f} / 100")
            print("   Skills               :", ", ".join(candidate["skills"]) if candidate["skills"] else "None")

    print("\n")
    print("=" * 70)
    print("                     OPTIMIZATION RESULT")
    print("=" * 70)
    print("Proposed Additional Allocation:", f"{proposed:.2f}%")
    print("Projected Project Allocation :", f"{current_allocation + proposed:.2f}%")
    print("Remaining Gap                :", f"{remaining_gap:.2f}%")
    print("Plan Status                  :", "FULL GAP COVERAGE" if remaining_gap < 0.01 else "PARTIAL GAP COVERAGE")
    print("Average Selected Skill Match :", f"{weighted_skill:.2f}%")
    print("Optimization Confidence      :", f"{confidence:.2f} / 100")

    if remaining_gap < 0.01 and weighted_skill >= 75:
        recommendation = "Strong plan: full gap coverage with strong skill alignment."
    elif remaining_gap < 0.01:
        recommendation = "Plan covers the full gap, but review skill alignment before execution."
    elif proposed > 0:
        recommendation = "Use the proposed safe allocations and resolve the remaining gap separately."
    else:
        recommendation = "No safe plan available; rebalance existing resources first."

    print("Recommendation              :", recommendation)
    print("\n⚠️ Advisory only: no database allocation was changed by Version 30.")
    print("=" * 70)



# ============================================================
# VERSION 31 - EXECUTIVE DASHBOARD & KPI ANALYTICS
# ============================================================

def executive_resource_dashboard():
    """Executive-level summary of resource allocation KPIs.
    Advisory/reporting only: this version does not change the database.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # --------------------------------------------------------
        # ORGANIZATION KPIs
        # --------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM employees;")
        total_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects;")
        total_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM allocations;")
        active_allocations = cursor.fetchone()[0]

        # --------------------------------------------------------
        # RESOURCE UTILIZATION
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                COALESCE(AVG(workload), 0),
                COALESCE(MAX(workload), 0),
                COUNT(*) FILTER (WHERE workload < 50),
                COUNT(*) FILTER (WHERE workload > 90),
                COUNT(*) FILTER (WHERE workload <= 90)
            FROM employees;
        """)
        employee_stats = cursor.fetchone()

        average_workload = float(employee_stats[0] or 0)
        highest_workload = float(employee_stats[1] or 0)
        underutilized = employee_stats[2]
        overloaded = employee_stats[3]
        available_employees = employee_stats[4]

        # --------------------------------------------------------
        # PROJECT STAFFING
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                p.name,
                p.priority,
                p.required_allocation,
                COALESCE(SUM(a.allocation_percentage), 0) AS current_allocation
            FROM projects p
            LEFT JOIN allocations a
                ON p.project_id = a.project_id
            GROUP BY p.project_id, p.name, p.priority, p.required_allocation
            ORDER BY p.project_id;
        """)
        projects_data = cursor.fetchall()

        fully_staffed = 0
        understaffed = 0
        critical_projects = 0
        project_scores = []
        project_alerts = []

        priority_rank = {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1
        }

        for name, priority, required, current in projects_data:
            required = float(required or 0)
            current = float(current or 0)
            gap = max(required - current, 0)

            if required <= 0:
                staffing_score = 100.0
            else:
                staffing_score = min((current / required) * 100, 100.0)

            project_scores.append(staffing_score)

            if current >= required:
                fully_staffed += 1
            else:
                understaffed += 1

            if gap > 0:
                if str(priority).strip().lower() == "critical":
                    critical_projects += 1
                elif gap >= max(required * 0.50, 20):
                    critical_projects += 1

                project_alerts.append({
                    "name": name,
                    "priority": priority,
                    "gap": gap,
                    "score": priority_rank.get(str(priority).strip().title(), 1)
                })

        project_staffing_score = (
            sum(project_scores) / len(project_scores)
            if project_scores else 100.0
        )

        # --------------------------------------------------------
        # RESOURCE BALANCE SCORE
        # Same philosophy as Version 26 so the dashboard remains
        # consistent with the existing health score.
        # --------------------------------------------------------
        if total_employees == 0:
            resource_balance_score = 100.0
        else:
            overload_penalty = (overloaded / total_employees) * 100
            underutilization_penalty = (underutilized / total_employees) * 50
            resource_balance_score = max(
                0.0,
                100.0 - overload_penalty - underutilization_penalty
            )

        overall_health = (
            project_staffing_score * 0.60
            + resource_balance_score * 0.40
        )

        if overall_health >= 80:
            status = "EXCELLENT"
        elif overall_health >= 60:
            status = "GOOD"
        elif overall_health >= 40:
            status = "NEEDS ATTENTION"
        else:
            status = "CRITICAL"

        # --------------------------------------------------------
        # HISTORICAL ACTIVITY
        # --------------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE UPPER(action) = 'ADD'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'MODIFY'),
                COUNT(*) FILTER (WHERE UPPER(action) = 'REMOVE')
            FROM allocation_history;
        """)
        history = cursor.fetchone()

        total_changes = history[0] or 0
        add_changes = history[1] or 0
        modify_changes = history[2] or 0
        remove_changes = history[3] or 0

        # --------------------------------------------------------
        # TOP PRIORITY ALERTS
        # --------------------------------------------------------
        project_alerts.sort(
            key=lambda item: (item["score"], item["gap"]),
            reverse=True
        )

        # --------------------------------------------------------
        # DISPLAY
        # --------------------------------------------------------
        print("\n")
        print("=" * 70)
        print("              SRA EXECUTIVE RESOURCE DASHBOARD")
        print("=" * 70)

        print("\n")
        print("ORGANIZATION KPIs")
        print("-" * 70)
        print(f"Employees                  : {total_employees}")
        print(f"Projects                   : {total_projects}")
        print(f"Active Allocations         : {active_allocations}")

        print("\n")
        print("RESOURCE HEALTH")
        print("-" * 70)
        print(f"Overall Resource Health    : {overall_health:.2f} / 100")
        print(f"Project Staffing Score     : {project_staffing_score:.2f} / 100")
        print(f"Resource Balance Score     : {resource_balance_score:.2f} / 100")
        print(f"Overall Status             : {status}")

        print("\n")
        print("PROJECT KPIs")
        print("-" * 70)
        print(f"Fully Staffed Projects     : {fully_staffed}")
        print(f"Understaffed Projects      : {understaffed}")
        print(f"Critical / Major Alerts    : {critical_projects}")

        print("\n")
        print("RESOURCE UTILIZATION")
        print("-" * 70)
        print(f"Average Employee Workload  : {average_workload:.2f}%")
        print(f"Highest Employee Workload  : {highest_workload:.2f}%")
        print(f"Employees With Capacity    : {available_employees}")
        print(f"Underutilized Employees    : {underutilized}")
        print(f"Overloaded Employees       : {overloaded}")

        print("\n")
        print("DECISION ALERTS")
        print("-" * 70)

        if not project_alerts:
            print("✓ No project staffing gaps detected.")
        else:
            for index, alert in enumerate(project_alerts[:5], 1):
                print(
                    f"{index}. [{str(alert['priority']).upper()}] "
                    f"{alert['name']} → {alert['gap']:.2f}% resource gap"
                )

        print("\n")
        print("HISTORICAL ACTIVITY")
        print("-" * 70)
        print(f"Total Allocation Changes   : {total_changes}")
        print(f"ADD Changes                 : {add_changes}")
        print(f"MODIFY Changes              : {modify_changes}")
        print(f"REMOVE Changes              : {remove_changes}")

        print("\n")
        print("EXECUTIVE RECOMMENDATION")
        print("-" * 70)

        if project_alerts:
            top = project_alerts[0]
            print(f"Top Priority Project        : {top['name']}")
            print(
                f"Primary Action              : "
                f"Address the {top['gap']:.2f}% staffing gap."
            )
        else:
            print("Top Priority Project        : None")
            print("Primary Action              : Maintain current allocation strategy.")

        if overloaded > 0:
            print("Capacity Recommendation     : Review overloaded employees.")
        elif underutilized > 0 and project_alerts:
            print("Capacity Recommendation     : Consider targeted redistribution from underutilized resources.")
        else:
            print("Capacity Recommendation     : Current employee capacity is balanced.")

        print("\n")
        print("SYSTEM STATUS")
        print("-" * 70)
        if overall_health >= 80:
            system_recommendation = "Maintain current resource strategy."
        elif overall_health >= 60:
            system_recommendation = "Targeted resource adjustments can improve performance."
        elif overall_health >= 40:
            system_recommendation = "Resource redistribution is recommended."
        else:
            system_recommendation = "Immediate resource reallocation is recommended."

        print(f"System Recommendation       : {system_recommendation}")
        print("\n⚠️ Executive dashboard is advisory only; no database allocation was changed.")
        print("=" * 70)

    except Exception as error:
        print("\n❌ EXECUTIVE DASHBOARD FAILED")
        print("Reason:", error)

    finally:
        cursor.close()
        connection.close()



# ============================================================
# VERSION 32 - SYSTEM HARDENING & VALIDATION
# ============================================================

def system_validation_integrity_check():
    """Run a read-only integrity audit over core resource-allocation data."""
    print("\n")
    print("=" * 70)
    print("              SYSTEM VALIDATION & INTEGRITY CHECK")
    print("=" * 70)

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        issues = []
        warnings = []

        # Employees: invalid numeric ranges and inconsistent capacity.
        cursor.execute("""
            SELECT employee_id, name, experience, availability, workload
            FROM employees
            ORDER BY employee_id;
        """)
        employees = cursor.fetchall()

        for employee_id, name, experience, availability, workload in employees:
            experience = float(experience or 0)
            availability = float(availability or 0)
            workload = float(workload or 0)

            if experience < 0:
                issues.append(f"Employee {employee_id} ({name}): negative experience.")
            if not 0 <= availability <= 100:
                issues.append(f"Employee {employee_id} ({name}): availability outside 0-100%.")
            if not 0 <= workload <= 100:
                issues.append(f"Employee {employee_id} ({name}): workload outside 0-100%.")

        # Projects: invalid required allocation and priority values.
        cursor.execute("""
            SELECT project_id, name, priority, required_allocation
            FROM projects
            ORDER BY project_id;
        """)
        projects = cursor.fetchall()

        for project_id, name, priority, required in projects:
            required = float(required or 0)
            if required <= 0 or required > 100:
                issues.append(f"Project {project_id} ({name}): required allocation outside 0-100%.")
            if str(priority).capitalize() not in {"High", "Medium", "Low"}:
                warnings.append(f"Project {project_id} ({name}): unexpected priority '{priority}'.")

        # Allocations: invalid percentages, missing references, and per-employee overload.
        cursor.execute("""
            SELECT allocation_id, employee_id, project_id, allocation_percentage
            FROM allocations
            ORDER BY allocation_id;
        """)
        allocations = cursor.fetchall()

        for allocation_id, employee_id, project_id, percentage in allocations:
            percentage = float(percentage or 0)
            if percentage <= 0 or percentage > 100:
                issues.append(f"Allocation {allocation_id}: percentage outside 0-100%.")

        cursor.execute("""
            SELECT employee_id, COALESCE(SUM(allocation_percentage), 0)
            FROM allocations
            GROUP BY employee_id
            HAVING COALESCE(SUM(allocation_percentage), 0) > 100.01;
        """)
        overloaded_allocations = cursor.fetchall()

        for employee_id, total in overloaded_allocations:
            issues.append(
                f"Employee {employee_id}: allocation records total {float(total):.2f}%, exceeding 100%."
            )

        # Detect duplicate employee-project allocation records.
        cursor.execute("""
            SELECT employee_id, project_id, COUNT(*)
            FROM allocations
            GROUP BY employee_id, project_id
            HAVING COUNT(*) > 1;
        """)
        duplicates = cursor.fetchall()

        for employee_id, project_id, count in duplicates:
            warnings.append(
                f"Employee {employee_id} has {count} allocation records for project {project_id}."
            )

        # Detect allocations that reference missing entities. Foreign keys should prevent these.
        cursor.execute("""
            SELECT COUNT(*)
            FROM allocations a
            LEFT JOIN employees e ON e.employee_id = a.employee_id
            LEFT JOIN projects p ON p.project_id = a.project_id
            WHERE e.employee_id IS NULL OR p.project_id IS NULL;
        """)
        orphaned = cursor.fetchone()[0]
        if orphaned:
            issues.append(f"Found {orphaned} orphaned allocation record(s).")

        print("\n")
        print("DATABASE CONNECTIVITY")
        print("-" * 70)
        print("PostgreSQL Connection       : OK")

        print("\n")
        print("DATA VALIDATION")
        print("-" * 70)
        print(f"Employees Checked           : {len(employees)}")
        print(f"Projects Checked            : {len(projects)}")
        print(f"Allocations Checked         : {len(allocations)}")
        print(f"Critical Issues             : {len(issues)}")
        print(f"Warnings                    : {len(warnings)}")

        print("\n")
        print("VALIDATION RESULTS")
        print("-" * 70)

        if not issues:
            print("✓ No critical data-integrity violations detected.")
        else:
            for issue in issues[:10]:
                print("❌", issue)
            if len(issues) > 10:
                print(f"... and {len(issues) - 10} more issue(s).")

        if warnings:
            print("\nWARNINGS")
            for warning in warnings[:10]:
                print("⚠️", warning)
            if len(warnings) > 10:
                print(f"... and {len(warnings) - 10} more warning(s).")

        print("\n")
        print("SYSTEM HARDENING STATUS")
        print("-" * 70)

        if not issues and not warnings:
            status = "PASS - SYSTEM DATA IS HEALTHY"
            action = "No corrective action is currently required."
        elif not issues:
            status = "PASS WITH WARNINGS"
            action = "Review warnings during routine maintenance."
        else:
            status = "FAIL - CORRECTIVE ACTION REQUIRED"
            action = "Fix critical integrity issues before relying on analytics."

        print("Validation Status            :", status)
        print("Recommended Action           :", action)
        print("\n⚠️ Read-only audit: no database data was modified.")
        print("=" * 70)

    except Exception as error:
        print("\n❌ SYSTEM VALIDATION FAILED")
        print("Reason:", error)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()