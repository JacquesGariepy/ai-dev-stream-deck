"""Human UI language is independent of the English agent protocol."""
import locale
import os

STRINGS = {
    'mission_tab': ('Mission', 'Mission'), 'activity_tab': ('Activity & next actions', 'Activité et prochaines actions'),
    'factory_tab': ('Factory control', 'Pilotage Factory'),
    'deck_language': ('Apply language to Stream Deck', 'Appliquer la langue au Stream Deck'),
    'deck_note': ('Opens the standard profile import.', 'Ouvre l’import normal du profil.'),
    'work': ('Work', 'Travail'), 'personal': ('Personal', 'Personnel'),
    'state': ('State', 'État'), 'created': ('Created', 'Créée'), 'reload': ('Refresh', 'Actualiser'),
    'next_action': ('Prepare next mission', 'Préparer la suite'),
    'activity_note': ('Local sessions refresh every 4 seconds. Select a session for evidence and the next suggested action.', 'Les sessions locales sont actualisées toutes les 4 secondes. Sélectionne une session pour voir les éléments disponibles et la suite proposée.'),
    'no_sessions': ('No local session yet.', 'Aucune session locale pour le moment.'),
    'prepared': ('Prepared', 'Préparée'), 'running': ('Running', 'En cours'), 'exited': ('Exited', 'Terminée'),
    'interrupted': ('Runner no longer active', 'Processus de session arrêté'), 'launch_error': ('Launch error', 'Erreur de lancement'),
    'failed': ('Nonzero exit code', 'Code de sortie en erreur'), 'unknown': ('Unknown', 'Inconnu'),
    'unconfirmed': ('Launch not confirmed', 'Lancement non confirmé'),
    'next_prepared': ('Waiting for the session runner to report that it started.', 'En attente de la confirmation du démarrage de la session.'),
    'exit_code': ('Exit code', 'Code de sortie'),
    'unverified': ('Objective outcome: unverified. An exit code is not evidence of completion.', 'Résultat de l’objectif : non vérifié. Un code de sortie ne prouve pas sa réalisation.'),
    'unmeasured': ('Provider tokens and cost: not measured.', 'Tokens et coût du fournisseur : non mesurés.'),
    'next_verify': ('Next: prepare an independent verification of the changes.', 'Suite proposée : préparer une vérification des changements.'),
    'next_diagnose': ('Next: prepare a diagnosis using the previous session evidence.', 'Suite proposée : préparer un diagnostic de la session précédente.'),
    'next_wait': ('Next: check the active terminal for progress or approval requests.', 'Suite : consulter le terminal pour l’avancement ou les demandes d’approbation.'),
    'factory_note': ('Direct access to your installed Factory and its canonical tasks, decisions and controls. The Factory repository is separate from the mission project folder.', 'Accès direct à ta Factory installée, à ses tâches, décisions et contrôles officiels. Son dépôt est indépendant du dossier choisi pour les missions.'),
    'factory_select': ('Choose Factory folder', 'Choisir le dossier Factory'),
    'factory_open': ('Open Factory workbench', 'Ouvrir le tableau de bord Factory'),
    'not_configured': ('Not configured', 'Non configuré'),
    'factory_load': ('Refresh to read real Factory status. Open the workbench to operate it.', 'Actualise pour lire l’état réel de Factory. Ouvre son tableau de bord pour la piloter.'),
    'loading': ('Reading current state…', 'Lecture de l’état actuel…'),
    'unavailable': ('State unavailable', 'État indisponible'),
    'tasks': ('Canonical task states', 'États des tâches officielles'),
    'active_attempts': ('Executing attempts reported by Factory', 'Tentatives en cours signalées par Factory'),
    'decisions': ('Pending decisions', 'Décisions en attente'),
    'budget_pending': ('Budget decision required before autonomous execution.', 'Décision de budget requise avant l’exécution autonome.'),
    'registration_pending': ('Registration checks are pending (quality commands / Windows paths).', 'Vérifications d’enregistrement en attente (commandes qualité / chemins Windows).'),
    'factory_next_blocked': ('Next: open the workbench and resolve the pending decision before starting an autonomous run.', 'Suite : ouvrir le tableau de bord et régler la décision en attente avant un lancement autonome.'),
    'factory_next': ('Next: open the workbench to select tasks and use Factory’s execution controls.', 'Suite : ouvrir le tableau de bord pour sélectionner les tâches et utiliser les contrôles de Factory.'),
    'blocked': ('Blocked', 'Bloquées'), 'captured': ('Captured', 'Capturées'), 'closed': ('Closed', 'Clôturées'),
    'executing': ('Execution state (not live agent count)', 'État exécution (pas le nombre d’agents actifs)'),
    'verification': ('Verification', 'Vérification'),
    'task_ready': ('Ready', 'Prêtes'),
    'browsers': ('Web browsers','Navigateurs web'),
    'ask_browser': ('Ask me before each web opening','Me demander avant chaque ouverture web'),
    'browser_note': ('Choose Edge or Chrome for each context. Web buttons use the active context and the browser\'s existing session.', 'Choisis Edge ou Chrome pour chaque contexte. Les boutons web utilisent le contexte actif et la session existante du navigateur.'),
    'web_context': ('Active context','Contexte actif'),
    'save': ('Save','Enregistrer'), 'save_open': ('Save and open','Enregistrer et ouvrir'),
    'refactor': ('Refactor','Simplifier'), 'explain': ('Explain','Expliquer'),
    'performance': ('Performance','Performance'), 'security': ('Security','Sécurité'),
    'docs': ('Docs','Docs'), 'usage': ('Usage','Usage'), 'pr_draft': ('PR draft','Brouillon PR'),
    'title': ('AI Dev — Control Panel', 'AI Dev — Panneau de contrôle'),
    'heading': ('AI Dev — Agent control center', 'AI Dev — Centre de pilotage des agents'),
    'project': ('Project folder', 'Dossier du projet'),
    'browse': ('Browse…', 'Choisir…'),
    'harness': ('Harness', 'Outil IA'),
    'profile': ('PowerShell profile', 'Profil PowerShell'),
    'workflow': ('Workflow', 'Type de travail'),
    'language': ('Interface language', 'Langue de l’interface'),
    'objective': ('Agent objective (English)', 'Objectif pour l’IA (en anglais)'),
    'launch': ('Launch mission', 'Lancer la mission'),
    'open': ('Open session', 'Ouvrir une session'),
    'refresh': ('Detect again', 'Détecter à nouveau'),
    'sessions': ('Sessions', 'Sessions'),
    'context': ('Collect Git context', 'Collecter le contexte Git'),
    'default': ('Default profile', 'Profil par défaut'),
    'none': ('No harness detected. Install a CLI or check your PowerShell profile.', 'Aucun outil détecté. Installe une CLI ou vérifie ton profil PowerShell.'),
    'ready': ('Ready to launch; authentication not checked.', 'Prêt à lancer ; authentification non vérifiée.'),
    'missing': ('Command found, but its CLI is unavailable.', 'Commande détectée, mais sa CLI est introuvable.'),
    'uninitialized': ('Profile will be initialized by its PowerShell launcher; sign-in may be needed.', 'Le lanceur PowerShell initialisera ce profil ; une connexion peut être nécessaire.'),
    'note': ('Agent instructions and responses use English. Your UI language is separate. No API keys required by this launcher.', 'Les consignes et réponses des IA sont en anglais. La langue de l’interface est indépendante. Ce lanceur ne demande aucune clé API.'),
    'unknown_adapter': ('Interactive session only: this harness has no mission adapter yet.', 'Session interactive seulement : cet outil n’a pas encore d’adaptateur de mission.'),
    'english_confirm': ('My objective is written in English (code, paths and names may remain unchanged).', 'Mon objectif est rédigé en anglais (code, chemins et noms peuvent rester inchangés).'),
    'english_required': ('Write the objective in English and confirm it before sending.', 'Rédige l’objectif en anglais et confirme-le avant l’envoi.'),
    'select': ('Choose a harness and profile.', 'Choisis un outil et un profil.'),
    'saved_context': ('Git context saved locally.', 'Contexte Git enregistré localement.'),
    'error': ('AI Dev error', 'Erreur AI Dev'),
    'implement': ('Implement', 'Implémenter'), 'plan': ('Plan', 'Planifier'),
    'debug': ('Debug', 'Diagnostiquer'), 'review': ('Review', 'Revoir'),
    'test': ('Test', 'Tester'), 'handoff': ('Handoff', 'Passer le relais'),
}


def windows_locale():
    if os.name == 'nt':
        import ctypes
        buffer = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
            return buffer.value
    return locale.getlocale()[0] or 'en-US'


def resolve_language(preference='auto', detected=None):
    if preference in ('en', 'fr'):
        return preference
    tag = (detected if detected is not None else windows_locale()).lower().replace('_', '-')
    return 'fr' if tag.split('-')[0] == 'fr' else 'en'


def tr(key, language):
    return STRINGS[key][1 if language == 'fr' else 0]
