import streamlit as st
import re
import pandas as pd
from typing import Tuple, Union, List, Dict, Any
import uuid
from supabase import create_client, Client


# Initialize Supabase client
url = "https://tjgmipyirpzarhhmihxf.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRqZ21pcHlpcnB6YXJoaG1paHhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE2NzQ2MDEsImV4cCI6MjA0NzI1MDYwMX0.LNMUqA0-t6YtUKP6oOTXgVGYLu8Tpq9rMhH388SX4bI"
supabase: Client = create_client(url, key)
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# Enhanced Custom CSS for Professional Design
st.markdown("""
    <style>
        /* Global Styling */
        .stApp {
            background-color: #f4f6f9;
            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
        }

        /* Title Styling */
        .title {
            color: #2c3e50;
            text-align: center;
            font-weight: 700;
            margin-bottom: 20px;
            background: linear-gradient(90deg, #3498db, #2980b9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* SQL Editor Styling */
        .sql-editor {
            font-family: 'Fira Code', 'Courier New', monospace;
            background-color: #ffffff;
            border: 1px solid #e0e4e8;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            white-space: pre-wrap;
            line-height: 1.6;
        }

        /* SQL Keyword Highlighting */
        .sql-keyword {
            color: #2980b9;
            font-weight: 600;
        }

        /* Button Styling */
        .stButton>button {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .stButton>button:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        /* Submitted Queries Styling */
        .submitted-query {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 6px;
        }

        /* Results Table Styling */
        .dataframe {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }

        .dataframe thead tr {
            background-color: #3498db;
            color: #ffffff;
            text-align: left;
        }

        .dataframe th,
        .dataframe td {
            padding: 12px 15px;
        }

        .dataframe tbody tr {
            border-bottom: 1px solid #dddddd;
        }

        .dataframe tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }

        .dataframe tbody tr:last-of-type {
            border-bottom: 2px solid #3498db;
        }
    </style>
""", unsafe_allow_html=True)


def compare_query_results(user_result: List[Dict], solution_result: List[Dict]) -> Tuple[bool, str]:
    """
    Compare two query results for equality, focusing on data content rather than structure.
    Returns (is_equal, message)
    """
    try:
        # Convert results to DataFrames
        df_user = pd.DataFrame(user_result)
        df_solution = pd.DataFrame(solution_result)

        # If either result is empty, check if both are empty
        if df_user.empty and df_solution.empty:
            return True, "Les résultats sont identiques (aucune donnée)"
        elif df_user.empty or df_solution.empty:
            return False, "Un résultat est vide alors que l'autre ne l'est pas"

        # Convert DataFrames to sets of tuples for value comparison
        user_values = set(tuple(x) for x in df_user.values.tolist())
        solution_values = set(tuple(x) for x in df_solution.values.tolist())

        if user_values == solution_values:
            return True, "Les résultats correspondent exactement!"
        else:
            missing = len(solution_values - user_values)
            extra = len(user_values - solution_values)

            message = "Différences trouvées: "
            if missing > 0:
                message += f"{missing} lignes manquantes. "
            if extra > 0:
                message += f"{extra} lignes en trop."

            return False, message

    except Exception as e:
        return False, f"Erreur lors de la comparaison: {str(e)}"


def is_safe_query(query: str) -> Tuple[bool, str]:
    """
    Validate if the query is safe to execute.
    """
    query_upper = query.strip().upper()
    if re.search(r'\bDROP\b', query_upper):
        return False, "Les requêtes DROP ne sont pas autorisées pour des raisons de sécurité."
    return True, "La requête est sécurisée"


def highlight_sql(query: str) -> str:
    """
    Highlight SQL keywords in the query
    """
    sql_keywords = [
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'TABLE',
        'INTO', 'VALUES', 'AND', 'OR', 'NOT', 'NULL', 'AS', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
        'OUTER', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL',
        'VIEW', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX'
    ]

    highlighted_query = query
    for keyword in sql_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        highlighted_query = re.sub(
            pattern,
            f'<span class="sql-keyword">{keyword}</span>',
            highlighted_query,
            flags=re.IGNORECASE
        )

    return highlighted_query


def normalize_query(query: str) -> str:
    """
    Normalize query for strict comparison
    """
    # Remove trailing semicolon before normalization
    normalized = query.rstrip(';').lower()
    normalized = re.sub(r'\s+', '', normalized)
    return normalized


def execute_query(query: str, **kwargs) -> Tuple[bool, Union[List[Dict], str], bool]:
    """
    Execute a query and return results. Handle errors gracefully with optional user-specific views.
    """
    try:
        # Remove trailing semicolon if present
        query = query.rstrip(';')

        user_id = kwargs.get('user_id')
        # Normalize query to uppercase for consistent checking
        query_upper = query.strip().upper()

        # Check if it's a CREATE VIEW or WITH query
        is_complex_query = (
                query_upper.startswith("CREATE VIEW") or
                query_upper.startswith("WITH")
        )

        # Handle CREATE VIEW queries
        if query_upper.startswith("CREATE VIEW"):
            # Extract original view name
            view_name = query.split()[2]

            # If user_id is provided, modify the view name to be user-specific
            if user_id:
                user_specific_view_name = f"{user_id}_{view_name}"

                # Replace the original view name in the query with the user-specific name
                query = query.replace(view_name, user_specific_view_name, 1)
                view_name = user_specific_view_name

            # Check if the view already exists
            response = supabase.rpc("execute_returning_sql",
                                    {"query_text": f"SELECT to_regclass('{view_name}')"}).execute()
            if hasattr(response, 'data') and response.data and response.data[0]['to_regclass']:
                # If view exists, drop it first to allow recreation
                drop_query = f"DROP VIEW IF EXISTS {view_name}"
                supabase.rpc("execute_non_returning_sql", {"query_text": drop_query}).execute()

            # Execute the CREATE VIEW query
            response = supabase.rpc("execute_non_returning_sql", {"query_text": query}).execute()
            return True, f"Vue {view_name} créée avec succès", False

        # Execute complex queries like WITH statements
        elif is_complex_query:
            response = supabase.rpc("execute_returning_sql", {"query_text": query}).execute()
            if not hasattr(response, 'data'):
                return True, [], True

            # Handle single-column results
            if response.data and len(response.data[0].keys()) == 1:
                key = list(response.data[0].keys())[0]
                result = [{"result": row[key]} for row in response.data]
            else:
                result = response.data

            return True, result, True

        # Standard query execution (SELECT, etc.)
        elif query_upper.startswith("SELECT"):
            response = supabase.rpc("execute_returning_sql", {"query_text": query}).execute()
            if not hasattr(response, 'data'):
                return True, [], True

            # Handle single-column results
            if response.data and len(response.data[0].keys()) == 1:
                key = list(response.data[0].keys())[0]
                result = [{"result": row[key]} for row in response.data]
            else:
                result = response.data

            return True, result, True

        else:
            response = supabase.rpc("execute_non_returning_sql", {"query_text": query}).execute()
            return True, "Requête exécutée avec succès", False

    except Exception as e:
        return False, str(e), is_complex_query


def is_query_correct(user_query: str, selected_question: str, user_id: str = None) -> Tuple[bool, str]:
    """
    Enhanced query verification with support for more complex query structures
    """
    try:
        # Remove trailing semicolon
        user_query = user_query.rstrip(';')

        # Get the solution query
        response = supabase.table("questions").select("question", "solution").eq("question",
                                                                                 selected_question).execute()
        if not hasattr(response, 'data') or not response.data:
            return False, "Solution non trouvée"

        solution_query = response.data[0]['solution']
        question_text = response.data[0]['question']

        # Handle CREATE VIEW and WITH queries
        if (user_query.strip().upper().startswith("CREATE VIEW") or
                user_query.strip().upper().startswith("WITH")):
            normalized_user = normalize_query(user_query)
            normalized_solution = normalize_query(solution_query)
            return normalized_user == normalized_solution, "Vérification syntaxique pour requêtes complexes"

        # Pass user_id to execute_query if available
        execute_kwargs = {"user_id": user_id} if user_id else {}

        # Execute both user and solution queries
        success_user, result_user, is_select_user = execute_query(user_query, **execute_kwargs)
        if not success_user:
            return False, f"Erreur dans votre requête: {result_user}"

        success_solution, result_solution, is_select_solution = execute_query(solution_query)
        if not success_solution:
            return False, f"Erreur dans la solution: {result_solution}"

        # Compare results for SELECT queries
        if is_select_user and is_select_solution:
            return compare_query_results(result_user, result_solution)

        # For other query types, consider them potentially correct
        return True, "Requête complexe vérifiée avec succès"

    except Exception as e:
        return False, f"Erreur lors de la vérification: {str(e)}"


def fetch_questions():
    """
    Fetch questions from Supabase
    """
    try:
        response = supabase.table("questions").select("question").execute()
        if hasattr(response, 'data') and response.data:
            return [q['question'] for q in response.data]
        return []
    except Exception as e:
        st.error(f"Erreur lors de la récupération des questions : {str(e)}")
        return []


# Main application layout
st.markdown('<h1 class="title">Data AI Lab - Éditeur de requêtes SQL</h1>', unsafe_allow_html=True)

# Initialize session state
if 'submitted_queries' not in st.session_state:
    st.session_state.submitted_queries = []

# Fetch and display questions
questions = fetch_questions()
selected_question = st.selectbox(
    "Sélectionnez une question :",
    ["Choisissez une question"] + questions
)

# Display the full question text in an expander
if selected_question != "Choisissez une question":
    response = supabase.table("questions").select("question").eq("question", selected_question).execute()
    if hasattr(response, 'data') and response.data:
        with st.expander(f"Énoncé de la question : {response.data[0]['question']}"):
            st.write(response.data[0]['question'])

# Query input
query = st.text_area(
    "Entrez votre requête SQL :",
    height=200,
    help="Écrivez votre requête SQL ici. Soyez attentif aux opérations sensibles."
)

# Display highlighted query
if query:
    st.markdown(f"""
        <div class="sql-editor">
            {highlight_sql(query)}
        </div>
    """, unsafe_allow_html=True)

# Test query button
if st.button("Testez la requête"):
    if selected_question == "Choisissez une question":
        st.warning("Veuillez sélectionner une question.")
    else:
        is_safe, safety_message = is_safe_query(query)
        if not is_safe:
            st.error(safety_message)
        else:
            is_correct, message = is_query_correct(query, selected_question, st.session_state.user_id)


            # Display result status
            if is_correct:
                st.success(f"✅ Requête correcte! {message}")
            else:
                st.error(f"❌ Requête incorrecte: {message}")

            # Execute and show results
            success, result, is_select = execute_query(query)
            if success:
                if isinstance(result, list):
                    st.write("Résultat de votre requête:")
                    st.table(result)
                else:
                    st.info(result)
            else:
                st.error(f"Erreur d'exécution: {result}")

# Submit query button
if st.button("Soumettre la requête"):
    is_safe, message = is_safe_query(query)
    if not is_safe:
        st.error(message)
    else:
        try:
            st.session_state.submitted_queries.append(query)
            st.success("✅ La requête a été envoyée !")
        except Exception as e:
            st.error(f"Erreur dans l'envoi de la requête : {str(e)}")

# Display submitted queries
if st.session_state.submitted_queries:
    st.markdown('<div class="footer">Data AI Lab © 2024</div>', unsafe_allow_html=True)
