# -*- coding: utf-8 -*-
"""
Une mini-application Flask pour servir le tableau de bord d'audit IAM en plusieurs pages distinctes.
Version refactorisée utilisant une structure de projet standard avec des dossiers `templates` et `static`.
"""
import os
import json
from flask import Flask, jsonify, render_template, abort

# ==============================================================================
# 1. INITIALISATION DE L'APPLICATION FLASK
# ==============================================================================
app = Flask(__name__)

# ==============================================================================
# 2. ROUTES FLASK
# Chaque fonction correspond à une page de l'application et rend un template HTML.
# ==============================================================================

@app.route('/')
def effective_access_view():
    return render_template('effective_access.html', page='effective-access')

@app.route('/users')
def by_user_view():
    return render_template('by_user.html', page='by-user')

@app.route('/groups')
def by_group_view():
    return render_template('by_group.html', page='by-group')

@app.route('/user-details')
def user_details_view():
    return render_template('user_details.html', page='user-details')

@app.route('/stats/<stat_name>')
def summary_view(stat_name):
    valid_stats = [
        'users-per-role-project', 'members-per-group', 'access-per-group', 
        'direct-access-count', 'groups-per-user'
    ]
    if stat_name not in valid_stats:
        abort(404)
    
    # Titres pour chaque page de statistiques
    titles = {
        'users-per-role-project': 'User Count per (Role@Project)',
        'members-per-group': 'Member Count per Group',
        'access-per-group': 'Access Count per Group',
        'direct-access-count': 'Direct Access Count per User',
        'groups-per-user': 'Group Count per User'
    }

    return render_template('stats.html', page='stats', stat_key=stat_name, title=titles[stat_name])

@app.route('/api/data')
def get_all_data():
    """Charge et retourne toutes les données JSON nécessaires au tableau de bord."""
    json_files = {
        'effective': 'effective_access_by_role_project.json',
        'direct': 'user_direct_access.json',
        'membership': 'user_group_membership.json',
        'groupAccess': 'group_access_summary.json',
        'summary': 'numerical_summary.json',
        'userDetails': 'user_effective_access_details.json'
    }
    all_json_data = {}
    for key, filename in json_files.items():
        filepath = os.path.join('json', filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_json_data[key] = json.load(f)
        except FileNotFoundError:
            abort(404, description=f"Fichier de données manquant : {filename}")
        except json.JSONDecodeError:
            abort(500, description=f"Erreur de format dans le fichier : {filename}")
    return jsonify(all_json_data)

# ==============================================================================
# 3. POINT D'ENTRÉE DE L'APPLICATION
# ==============================================================================
if __name__ == '__main__':
    print("Lancement du serveur Flask...")
    print("Ouvrez votre navigateur et allez sur http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
