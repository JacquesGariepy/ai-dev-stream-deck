"""Human UI language is independent of the English agent protocol."""
import locale
import os

STRINGS = {
    'browsers': ('Web browsers','Navigateurs web'),
    'ask_browser': ('Ask me before each web opening','Me demander avant chaque ouverture web'),
    'browser_note': ('Choose Edge or Chrome for each context. Web buttons use the active context and the browser\'s existing session.', 'Choisis Edge ou Chrome pour chaque contexte. Les boutons web utilisent le contexte actif et la session existante du navigateur.'),
    'web_context': ('Active context','Contexte actif'),
    'save': ('Save','Enregistrer'), 'save_open': ('Save and open','Enregistrer et ouvrir'),
    'refactor': ('Refactor','Simplifier'), 'explain': ('Explain','Expliquer'),
    'performance': ('Performance','Performance'), 'security': ('Security','Sécurité'),
    'docs': ('Docs','Docs'), 'usage': ('Usage','Usage'), 'pr_draft': ('PR draft','Brouillon PR'),
    'title': ('AI Dev — Control Panel', 'AI Dev — Panneau de contrôle'),
    'heading': ('Give your agent an objective', 'Donne un objectif à ton agent'),
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
