import json
import os

from Programma_CS2_RENAN.core.config import get_resource_path
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.localization")


def _get_home_dir() -> str:
    """Return current home directory (evaluated at call time, not import time)."""
    return os.path.expanduser("~")


# Hardcoded TRANSLATIONS dict kept as fallback if JSON files fail to load.
TRANSLATIONS = {
    "en": {
        "app_name": "Macena CS2 Analyzer",
        "dashboard": "Dashboard",
        "coaching": "Coaching Insights",
        "settings": "Settings",
        "profile": "Player Profile",
        "no_insights": "No coaching insights available yet.",
        "pro_comparison": "Pro Player Analysis",
        "lang_name": "English",
        "upload_rules_title": "Upload Rules",
        "upload_rules_text": "1. .dem files only\n2. CS2 only\n3. 10/month limit",
        "visual_theme": "Visual Theme",
        "analysis_paths": "Analysis Paths",
        "appearance": "Appearance",
        "language": "Language",
        "cycle_wallpaper": "CYCLE WALLPAPER",
        "change_default_folder": "CHANGE DEFAULT FOLDER",
        "change_pro_folder": "CHANGE PRO FOLDER",
        "font_size": "Font Size",
        "font_type": "Font Type",
        "pro_knowledge": "Professional Knowledge",
        "upload_pro_desc": "Upload pro matches to train the Global Coach baseline.",
        "personalization": "Personalization & APIs",
        "upload_status": "Upload .dem files to train your personalized coach.",
        "tactical_analysis": "TACTICAL ANALYSIS",
        "tactical_desc": "Analyze match dynamics, grenade patterns, and spatial positioning.",
        "launch_viewer": "LAUNCH VIEWER",
        "coach_status": "Coach Status: ",
        "belief_state": "AI Confidence",
        "belief_desc": "How confident the AI is in its coaching analysis.",
        "inference_stability": "Status: ",
        "inference_high": "Ready",
        "inference_low": "Warming up \u2014 play matches to improve",
        "learning_intensity": "Analysis Speed",
        "learning_desc": "Increase to analyze your demos faster.",
        "causal_advantage": "Compare vs Pros",
        "audit_path": "HOW DID THE AI DECIDE THIS?",
        "pro_profile": "Pro Profile",
        "bio": "Bio",
        "system_specs": "System Specs",
        "sync_steam": "SYNC WITH STEAM",
        "settings_name": "Settings: Name",
        "ingame_name": "CS2 In-Game Name",
        "ingame_desc": "Enter the exact name you use in-game. This helps the AI identify you.",
        "nickname_hint": "In-Game Nickname",
        "settings_steam": "Settings: Steam",
        "steam_integration": "Steam Profile Integration",
        "steam_desc": "To sync your stats and matches, you need a 17-digit SteamID64.",
        "dev_api_support": "Developer API Support",
        "steam_key_hint": "Paste your Steam API Key here",
        "save_config": "SAVE CONFIGURATION",
        "settings_faceit": "Settings: FaceIT",
        "faceit_stats": "FaceIT Competitive Stats",
        "faceit_desc": "Connect your FaceIT account to compare your performance.",
        "faceit_hint": "Faceit API Client Key",
        "welcome": "Welcome",
        "next": "Next",
        "wizard_intro_title": "Welcome to Macena CS2 Analyzer",
        "wizard_intro_text": "This wizard will help you set up the 'Brain' storage and your demo folders.\n\nThe 'Brain' requires significant storage (>50GB recommended) for AI training data.",
        "wizard_start_btn": "Start Setup",
        "wizard_step1_title": "Step 1: The Brain Storage",
        "wizard_step1_desc": f"Select a folder for the Neural Network data.\n(Recommendation: Use a folder like {os.path.expanduser('~')}\\Documents\\DataCoach)",
        "wizard_step1_hint": "Or paste full path here",
        "wizard_select_folder": "Select Folder",
        "wizard_step2_title": "Step 2: Demo Input Folder",
        "wizard_step2_desc": "Select where you usually save your .dem files.",
        "wizard_finish_title": "Setup Complete",
        "wizard_finish_text": "Configuration saved!\n\nThe Background Daemon will now start to manage ingestion and training.\nPlease ensure Steam/FACEIT are running for best results.",
        "wizard_launch_btn": "Launch App",
        "tactical_analyzer": "Tactical Analyzer",
        "select_map": "Select Map",
        "select_round": "Select Round",
        "debug": "Debug",
        "select_dem": "SELECT .DEM FILES",
        "ingest_pro": "INGEST PRO DEMO",
        "medium": "MEDIUM",
        "high": "HIGH",
        "find_steam_id": "FIND MY STEAM ID (steamid.io)",
        "get_steam_key": "GET STEAM API KEY",
        "get_faceit_key": "GET FACEIT API KEY",
        "save_faceit": "SAVE FACEIT CONFIG",
        "player_name_default": "Player Name",
        "role_default": "Role: All-Rounder",
        "save": "SAVE",
        # F7-17: Quick action prompt i18n keys
        "quick_action_positioning": "How can I improve my positioning?",
        "quick_action_utility": "Analyze my utility usage",
        "quick_action_focus": "What should I focus on improving?",
        # F7-18: Hardcoded UI string i18n keys
        "training_progress": "Training Progress",
        "restart_service": "RESTART SERVICE",
        "upload_pro_demos": "Upload pro demos directly...",
        "ingestion_flux_speed": "Ingestion Flux Speed:",
        "rap_coach_dashboard": "AI Coach",
        "advanced_analytics": "Your Stats",
        "knowledge_engine": "Demo Processing",
        "ask_your_coach": "Ask Your Coach",
        "coach_thinking": "Coach is thinking...",
        "data_ingestion": "Data Ingestion",
        "match_history_title": "Match History",
        # F7-26: Missing search key
        "search": "Search",
        # P10-03: Baseline degraded warning (was hardcoded Portuguese in hybrid_engine.py)
        "baseline_degraded_warning": "WARNING: baseline_quality=degraded \u2014 using static fallback; coaching precision reduced",
        # F10-01: Dialog strings previously hardcoded in main.py
        "dialog_edit_profile": "Edit Profile",
        "dialog_cancel": "CANCEL",
        "dialog_save": "SAVE",
        "dialog_open_link": "Open External Link?",
        "dialog_cancel_lower": "Cancel",
        "dialog_open": "Open",
        "dialog_select_drive": "Select Drive",
        "dialog_ok": "OK",
        "dialog_close": "CLOSE",
        "dialog_tactical_lab": "Tactical Laboratory",
        "dialog_reconstructing": "Reconstructing 2D Dynamics...",
        "dialog_analysis_failed": "Analysis Failed",
        "dialog_skill_radar": "Skill Radar Analysis",
        "wizard_step2_hint": "Or paste demo folder path here",
    },
    "pt": {
        "app_name": "Macena CS2 Analisador",
        "dashboard": "Painel de Controle",
        "coaching": "Insights do Treinador",
        "settings": "Configurações",
        "profile": "Perfil",
        "no_insights": "Nenhum insight disponível ainda.",
        "pro_comparison": "Análise Profissional",
        "lang_name": "Português",
        "upload_rules_title": "Regras de Upload",
        "upload_rules_text": "1. Apenas arquivos .dem\n2. Apenas CS2\n3. Limite de 10/mês",
        "visual_theme": "Tema Visual",
        "analysis_paths": "Pastas de Análise",
        "appearance": "Aparência",
        "language": "Idioma",
        "cycle_wallpaper": "ALTERAR WALLPAPER",
        "change_default_folder": "ALTERAR PASTA PADRÃO",
        "change_pro_folder": "ALTERAR PASTA PRO",
        "font_size": "Tamanho da Fonte",
        "font_type": "Tipo de Fonte",
        "pro_knowledge": "Conhecimento Profissional",
        "upload_pro_desc": "Envie partidas profissionais para treinar a base Global.",
        "personalization": "Personalização & APIs",
        "upload_status": "Envie arquivos .dem para treinar seu treinador pessoal.",
        "tactical_analysis": "ANÁLISE TÁTICA",
        "tactical_desc": "Analise a dinâmica da partida, padrões de granadas e posicionamento.",
        "launch_viewer": "ABRIR ANALISADOR",
        "coach_status": "Status do Treinador: ",
        "belief_state": "Confian\u00e7a da IA",
        "belief_desc": "O quanto a IA confia na sua an\u00e1lise de coaching.",
        "inference_stability": "Status: ",
        "inference_high": "Pronta",
        "inference_low": "Aquecendo \u2014 jogue partidas para melhorar",
        "learning_intensity": "Velocidade de An\u00e1lise",
        "learning_desc": "Aumente para analisar seus demos mais r\u00e1pido.",
        "causal_advantage": "Comparar com Pros",
        "audit_path": "COMO A IA DECIDIU ISSO?",
        "pro_profile": "Perfil Profissional",
        "bio": "Biografia",
        "system_specs": "Especificações do Sistema",
        "sync_steam": "SINCRONIZAR COM STEAM",
        "settings_name": "Configurações: Nome",
        "ingame_name": "Nome no Jogo (CS2)",
        "ingame_desc": "Insira o nome exato que você usa no jogo para identificação da IA.",
        "nickname_hint": "Nickname no Jogo",
        "settings_steam": "Configurações: Steam",
        "steam_integration": "Integração de Perfil Steam",
        "steam_desc": "Para sincronizar, você precisa do SteamID64 de 17 dígitos.",
        "dev_api_support": "Suporte API de Desenvolvedor",
        "steam_key_hint": "Cole sua chave API Steam aqui",
        "save_config": "SALVAR CONFIGURAÇÃO",
        "settings_faceit": "Configurações: FaceIT",
        "faceit_stats": "Estatísticas FaceIT",
        "faceit_desc": "Conecte sua conta FaceIT para comparar seu desempenho.",
        "faceit_hint": "Chave de Cliente API FaceIT",
        "welcome": "Bem-vindo",
        "next": "Próximo",
        "wizard_intro_title": "Bem-vindo ao Macena CS2 Analisador",
        "wizard_intro_text": "Este assistente ajudará você a configurar o armazenamento do 'Cérebro' e suas pastas de demos.\n\nO 'Cérebro' requer armazenamento significativo (>50GB recomendado) para dados de treinamento de IA.",
        "wizard_start_btn": "Iniciar Configuração",
        "wizard_step1_title": "Passo 1: Armazenamento do Cérebro",
        "wizard_step1_desc": f"Selecione uma pasta para os dados da Rede Neural.\n(Recomendação: Use uma pasta como {os.path.expanduser('~')}\\Documents\\DadosTreinador)",
        "wizard_step1_hint": "Ou cole o caminho completo aqui",
        "wizard_select_folder": "Selecionar Pasta",
        "wizard_step2_title": "Passo 2: Pasta de Entrada de Demos",
        "wizard_step2_desc": "Selecione onde você costuma salvar seus arquivos .dem.",
        "wizard_finish_title": "Configuração Concluída",
        "wizard_finish_text": "Configuração salva!\n\nO Daemon de Segundo Plano agora começará a gerenciar a ingestão e o treinamento.\nPor favor, certifique-se de que a Steam/FACEIT estão rodando para melhores resultados.",
        "wizard_launch_btn": "Abrir Aplicativo",
        "tactical_analyzer": "Analisador Tático",
        "select_map": "Selecionar Mapa",
        "select_round": "Selecionar Round",
        "debug": "Debug",
        "select_dem": "SELECIONAR ARQUIVOS .DEM",
        "ingest_pro": "INGESTAR DEMO PRO",
        "medium": "MÉDIO",
        "high": "ALTO",
        "find_steam_id": "ENCONTRAR MEU STEAM ID (steamid.io)",
        "get_steam_key": "OBTER CHAVE API STEAM",
        "get_faceit_key": "OBTER CHAVE API FACEIT",
        "save_faceit": "SALVAR CONFIG FACEIT",
        "player_name_default": "Nome do Jogador",
        "role_default": "Função: Polivalente",
        "save": "SALVAR",
        # F7-17
        "quick_action_positioning": "Como posso melhorar meu posicionamento?",
        "quick_action_utility": "Analise meu uso de utilitários",
        "quick_action_focus": "No que devo focar para melhorar?",
        # F7-18
        "training_progress": "Progresso de Treino",
        "restart_service": "REINICIAR SERVIÇO",
        "upload_pro_demos": "Carregue demos profissionais...",
        "ingestion_flux_speed": "Velocidade de Ingestão:",
        "rap_coach_dashboard": "Coach IA",
        "advanced_analytics": "Suas Estat\u00edsticas",
        "knowledge_engine": "Processamento de Demos",
        "ask_your_coach": "Pergunte ao seu Coach",
        "coach_thinking": "Coach está pensando...",
        "data_ingestion": "Ingestão de Dados",
        "match_history_title": "Histórico de Partidas",
        # F7-26
        "search": "Buscar",
        # P10-03
        "baseline_degraded_warning": "AVISO: baseline_quality=degraded \u2014 usando valores est\u00e1ticos; precis\u00e3o do coaching reduzida",
        # F10-01
        "dialog_edit_profile": "Editar Perfil",
        "dialog_cancel": "CANCELAR",
        "dialog_save": "SALVAR",
        "dialog_open_link": "Abrir Link Externo?",
        "dialog_cancel_lower": "Cancelar",
        "dialog_open": "Abrir",
        "dialog_select_drive": "Selecionar Drive",
        "dialog_ok": "OK",
        "dialog_close": "FECHAR",
        "dialog_tactical_lab": "Laboratório Tático",
        "dialog_reconstructing": "Reconstruindo Dinâmicas 2D...",
        "dialog_analysis_failed": "Análise Falhou",
        "dialog_skill_radar": "Análise de Radar de Habilidades",
        "wizard_step2_hint": "Ou cole o caminho da pasta de demos aqui",
    },
    "it": {
        "app_name": "Macena CS2 Analizzatore",
        "dashboard": "Dashboard",
        "coaching": "Suggerimenti Coach",
        "settings": "Impostazioni",
        "profile": "Profilo",
        "no_insights": "Nessun consiglio disponibile ancora.",
        "pro_comparison": "Analisi Pro",
        "lang_name": "Italiano",
        "upload_rules_title": "Regole Caricamento",
        "upload_rules_text": "1. Solo file .dem\n2. Solo CS2\n3. Limite 10/mese",
        "visual_theme": "Tema Visivo",
        "analysis_paths": "Percorsi Analisi",
        "appearance": "Aspetto",
        "language": "Lingua",
        "cycle_wallpaper": "CAMBIA SFONDO",
        "change_default_folder": "CAMBIA CARTELLA DEFAULT",
        "change_pro_folder": "CAMBIA CARTELLA PRO",
        "font_size": "Dimensione Font",
        "font_type": "Tipo Font",
        "pro_knowledge": "Conoscenza Pro",
        "upload_pro_desc": "Carica partite pro per allenare la base del Global Coach.",
        "personalization": "Personalizzazione & API",
        "upload_status": "Carica file .dem per addestrare il tuo coach personale.",
        "tactical_analysis": "ANALISI TATTICA",
        "tactical_desc": "Analizza le dinamiche, i pattern di granate e il posizionamento.",
        "launch_viewer": "AVVIA ANALIZZATORE",
        "coach_status": "Stato Coach: ",
        "belief_state": "Fiducia dell'IA",
        "belief_desc": "Quanto l'IA \u00e8 sicura nella sua analisi di coaching.",
        "inference_stability": "Stato: ",
        "inference_high": "Pronta",
        "inference_low": "In riscaldamento \u2014 gioca partite per migliorare",
        "learning_intensity": "Velocit\u00e0 di Analisi",
        "learning_desc": "Aumenta per analizzare le tue demo pi\u00f9 velocemente.",
        "causal_advantage": "Confronta con i Pro",
        "audit_path": "COME HA DECISO L'IA?",
        "pro_profile": "Profilo Pro",
        "bio": "Bio",
        "system_specs": "Specifiche Sistema",
        "sync_steam": "SINCRONIZZA CON STEAM",
        "settings_name": "Impostazioni: Nome",
        "ingame_name": "Nome in Gioco (CS2)",
        "ingame_desc": "Inserisci il nome esatto usato in gioco per l'identificazione AI.",
        "nickname_hint": "Nickname in Gioco",
        "settings_steam": "Impostazioni: Steam",
        "steam_integration": "Integrazione Profilo Steam",
        "steam_desc": "Per sincronizzare, serve lo SteamID64 a 17 cifre.",
        "dev_api_support": "Supporto API Sviluppatore",
        "steam_key_hint": "Incolla qui la tua chiave API Steam",
        "save_config": "SALVA CONFIGURAZIONE",
        "settings_faceit": "Impostazioni: FaceIT",
        "faceit_stats": "Statistiche FaceIT",
        "faceit_desc": "Collega il tuo account FaceIT per confrontare le prestazioni.",
        "faceit_hint": "Chiave Client API FaceIT",
        "welcome": "Benvenuto",
        "next": "Avanti",
        "wizard_intro_title": "Benvenuto in Macena CS2 Analizzatore",
        "wizard_intro_text": "Questa procedura guidata ti aiuterà a configurare l'archiviazione del 'Cervello' e le tue cartelle demo.\n\nIl 'Cervello' richiede uno spazio di archiviazione significativo (>50GB consigliati) per i dati di addestramento AI.",
        "wizard_start_btn": "Inizia Configurazione",
        "wizard_step1_title": "Passo 1: Archiviazione del Cervello",
        "wizard_step1_desc": f"Seleziona una cartella per i dati della Rete Neurale.\n(Consiglio: usa una cartella como {os.path.expanduser('~')}\\Documents\\DatiCoach)",
        "wizard_step1_hint": "O incolla qui il percorso completo",
        "wizard_select_folder": "Seleziona Cartella",
        "wizard_step2_title": "Passo 2: Cartella di Input Demo",
        "wizard_step2_desc": "Seleziona dove di solito salvi i tuoi file .dem.",
        "wizard_finish_title": "Configurazione Completata",
        "wizard_finish_text": "Configurazione salvata!\n\nIl Daemon in background inizierà ora a gestire l'ingestione e l'allenamento.\nAssicurati che Steam/FACEIT siano in esecuzione per i migliori risultati.",
        "wizard_launch_btn": "Avvia Applicazione",
        "tactical_analyzer": "Analizzatore Tattico",
        "select_map": "Seleziona Mappa",
        "select_round": "Seleziona Round",
        "debug": "Debug",
        "select_dem": "SELEZIONA FILE .DEM",
        "ingest_pro": "INGESTA DEMO PRO",
        "medium": "MEDIO",
        "high": "ALTO",
        "find_steam_id": "TROVA IL MIO ID STEAM (steamid.io)",
        "get_steam_key": "OTTIENI CHIAVE API STEAM",
        "get_faceit_key": "OTTIENI CHIAVE API FACEIT",
        "save_faceit": "SALVA CONFIG FACEIT",
        "player_name_default": "Nome Giocatore",
        "role_default": "Ruolo: Tuttofare",
        "save": "SALVA",
        # F7-17
        "quick_action_positioning": "Come posso migliorare il mio posizionamento?",
        "quick_action_utility": "Analizza il mio uso degli utilitari",
        "quick_action_focus": "Su cosa dovrei concentrarmi per migliorare?",
        # F7-18
        "training_progress": "Progresso di Addestramento",
        "restart_service": "RIAVVIA SERVIZIO",
        "upload_pro_demos": "Carica demo professionali...",
        "ingestion_flux_speed": "Velocità di Ingestione:",
        "rap_coach_dashboard": "Coach IA",
        "advanced_analytics": "Le Tue Statistiche",
        "knowledge_engine": "Elaborazione Demo",
        "ask_your_coach": "Chiedi al tuo Coach",
        "coach_thinking": "Il coach sta pensando...",
        "data_ingestion": "Acquisizione Dati",
        "match_history_title": "Cronologia delle Partite",
        # F7-26
        "search": "Cerca",
        # P10-03
        "baseline_degraded_warning": "ATTENZIONE: baseline_quality=degraded \u2014 usando valori statici; precisione del coaching ridotta",
        # F10-01
        "dialog_edit_profile": "Modifica Profilo",
        "dialog_cancel": "ANNULLA",
        "dialog_save": "SALVA",
        "dialog_open_link": "Aprire Link Esterno?",
        "dialog_cancel_lower": "Annulla",
        "dialog_open": "Apri",
        "dialog_select_drive": "Seleziona Unità",
        "dialog_ok": "OK",
        "dialog_close": "CHIUDI",
        "dialog_tactical_lab": "Laboratorio Tattico",
        "dialog_reconstructing": "Ricostruzione Dinamiche 2D...",
        "dialog_analysis_failed": "Analisi Fallita",
        "dialog_skill_radar": "Analisi Radar Abilità",
        "wizard_step2_hint": "O incolla qui il percorso della cartella demo",
    },
}


def _load_json_translations() -> dict:
    """Load translations from JSON files in assets/i18n/."""
    loaded = {}
    i18n_dir = get_resource_path(os.path.join("assets", "i18n"))
    for lang_code in ("en", "pt", "it"):
        path = os.path.join(i18n_dir, f"{lang_code}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Expand {home_dir} placeholders
            for k, v in data.items():
                if isinstance(v, str) and "{home_dir}" in v:
                    data[k] = v.format(home_dir=_get_home_dir())
            loaded[lang_code] = data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            _logger.debug("JSON translation for '%s' unavailable: %s", lang_code, e)
    return loaded


# Load once at import time; fall back to hardcoded TRANSLATIONS per-key
_JSON_TRANSLATIONS = _load_json_translations()


# Kivy-dependent base class — guarded for Qt compatibility.
# When Kivy is absent, TRANSLATIONS and _JSON_TRANSLATIONS are still accessible.
try:
    from kivy.event import EventDispatcher
    from kivy.properties import StringProperty
except ImportError:
    EventDispatcher = object
    StringProperty = lambda default="": default


class LocalizationManager(EventDispatcher):
    lang = StringProperty("en")

    def get_text(self, key, trigger=None):
        """Returns translated text for the current language.

        LOC-02: Priority chain: JSON (current lang) -> hardcoded (current lang)
        -> hardcoded (English) -> raw key with warning.
        """
        # 1. JSON takes priority (most up-to-date)
        json_lang = _JSON_TRANSLATIONS.get(self.lang, {})
        value = json_lang.get(key)
        if value is not None:
            return value
        # 2. Hardcoded dict for current language
        hardcoded_lang = TRANSLATIONS.get(self.lang, {})
        value = hardcoded_lang.get(key)
        if value is not None:
            return value
        # 3. Hardcoded English fallback
        en_value = TRANSLATIONS.get("en", {}).get(key)
        if en_value is not None:
            return en_value
        # LOC-03: Log missing key so developers can spot untranslated strings
        _logger.debug("Missing translation key '%s' for lang '%s'", key, self.lang)
        return key

    def set_language(self, lang_code):
        """Updates the current language and triggers UI refresh."""
        if lang_code in TRANSLATIONS or lang_code in _JSON_TRANSLATIONS:
            self.lang = lang_code


# Singleton instance
i18n = LocalizationManager()
