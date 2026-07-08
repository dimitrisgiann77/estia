# -*- coding: utf-8 -*-
"""Piato — Module Εστίασης / Guest Experience (F&B). P-075 · Φ1: Ψηφιακό Μενού.

Plug-in: import από το ΤΕΛΟΣ του app.py (ΠΡΙΝ το init_db → create_all πιάνει τα μοντέλα).
Αυτόνομο module — ΞΕΧΩΡΙΣΤΟ από menu.py (admin nav) & GuestApp (room requests).

Φ1 (θεμέλιο — ΜΟΝΟ μενού):
  - Μοντέλα: Outlet -> MenuCategory -> MenuItem (+ItemVariant/ItemModifier) · Allergen(14 EU) · ItemAllergen.
  - Reuse Hotel/User με FK — καμία παράλληλη βάση, κανένα νέο «προσωπικό».
  - Owner-screen: ο F&B manager γράφει το μενού (/dashboard/piato)· ο πελάτης διαβάζει (public token).
  - Πολυγλωσσία (JSON ανά μεταφράσιμο πεδίο), αλλεργιογόνα 14 EU (EU 1169/2011), 86'd toggle.
  - Preview/publish: draft outlet -> δημόσιο 404, preview token ορατό· «Δημοσίευση» -> ανοίγει το κοινό.

ΟΧΙ σε Φ1: παραγγελίες/πληρωμές/κρατήσεις/KDS/PMS/loyalty/AI (Φ2-Φ4).
Spec: 02_MODULES_ESTIA/ΕΣΤΙΑΣΗ_PIATO/00_SPEC_PIATO.md
"""
import json, uuid
from datetime import datetime
from flask import request, redirect, url_for, render_template, abort, jsonify
from app import (app, db, current_user, is_admin, allowed_hotels, active_hotel_id,
                 log_activity, has_rank, ROLE_RANK, Hotel)


# ── Σταθερές ──────────────────────────────────────────────────────────────────
# Γλώσσες μενού (guest-facing· πρώτη = προεπιλογή/fallback). Εύκολα επεκτάσιμο.
# Γλώσσες μενού (guest-facing· πρώτη = προεπιλογή/fallback). Επεκτάσιμο.
PIATO_LANGS = [('el', 'Ελληνικά'), ('en', 'English'), ('de', 'Deutsch'),
               ('it', 'Italiano'), ('fr', 'Français')]
LANG_CODES = [c for c, _ in PIATO_LANGS]
DEF_LANG = 'el'

OUTLET_TYPES = [('restaurant', 'Εστιατόριο'), ('bar', 'Μπαρ'),
                ('pool_bar', 'Pool bar'), ('beach_bar', 'Beach bar'),
                ('room_service', 'Room service'), ('cafe', 'Café')]
OTYPE_LABEL = {k: v for k, v in OUTLET_TYPES}

# Παλέτες guest μενού (code, label). Πρώτη = προεπιλογή. (aegean = Boho Earth φωτεινό)
PIATO_PALETTES = [('olive', 'Olive & Brass'), ('aegean', 'Boho Earth (φωτεινό)'),
                  ('charcoal', 'Charcoal & Gold'), ('ink', 'Ink & Amber'),
                  ('linen', 'Linen & Sage (φωτεινό)')]
PALETTE_CODES = [c for c, _ in PIATO_PALETTES]

# Τρόποι παρουσίασης μενού (code, label). Πρώτη = προεπιλογή.
PIATO_LAYOUTS = [('grid', 'Πλέγμα (κάρτες)'), ('spread', 'Δίστηλο (magazine)'),
                 ('list', 'Λίστα (κλασική)')]
LAYOUT_CODES = [c for c, _ in PIATO_LAYOUTS]

# Ομαδοποίηση κατηγοριών σε δύο κύριες ενότητες (Φαγητό / Ποτό).
PIATO_KINDS = [('food', 'Φαγητό'), ('drink', 'Ποτό')]
KIND_CODES = [c for c, _ in PIATO_KINDS]

# UI strings guest μενού (σταθερά κείμενα) ανά γλώσσα. el = Ελληνικά· κάθε άλλη γλώσσα → en (διεθνές).
PIATO_UI = {
    'el': {'back': 'Πίσω', 'hide_allergens': 'Απόκρυψη αλλεργιογόνων', 'reset': 'Επαναφορά',
           'sold_out': 'εξαντλήθηκε', 'options': 'Επιλογές', 'extra': 'Extra', 'add': 'Προσθήκη',
           'my_order': 'Η παραγγελία μου', 'order_empty': 'Διαλέξτε πιάτα με το «＋ Προσθήκη».',
           'total': 'Σύνολο', 'order_note': 'Δείξτε την οθόνη στον σερβιτόρο για να καταχωρήσει την παραγγελία.',
           'clear': 'Καθαρισμός', 'order': 'Παραγγελία', 'questionnaire': 'Ερωτηματολόγιο',
           'allergen_note': 'Πληροφορίες αλλεργιογόνων διαθέσιμες κατόπιν αιτήματος',
           'no_match': 'Κανένα πιάτο δεν ταιριάζει με το φίλτρο.', 'preparing': 'Το μενού ετοιμάζεται…'},
    'en': {'back': 'Back', 'hide_allergens': 'Hide allergens', 'reset': 'Reset',
           'sold_out': 'sold out', 'options': 'Options', 'extra': 'Extras', 'add': 'Add',
           'my_order': 'My order', 'order_empty': 'Select dishes with the «＋ Add» button.',
           'total': 'Total', 'order_note': 'Show the screen to your waiter to place the order.',
           'clear': 'Clear', 'order': 'Order', 'questionnaire': 'Questionnaire',
           'allergen_note': 'Allergen information available on request',
           'no_match': 'No dishes match the filter.', 'preparing': 'The menu is being prepared…'},
}

def _ui(lang):
    return PIATO_UI.get(lang, PIATO_UI['en'])

# Γνωστές κατηγορίες ποτού (case-insensitive substrings, en/el) — για idempotent seed
# defaults ΜΟΝΟ όταν το kind δεν έχει οριστεί ακόμη. Ο admin πάντα υπερισχύει.
DRINK_NAME_HINTS = [
    'aperitif', 'sparkling', 'beer', 'wine', 'white wine', 'red wine', 'rose wine', 'rosé',
    'spirit', 'cocktail', 'brandy', 'whiskey', 'whisky', 'refreshment', 'coffee', 'tea',
    'juice', 'soft drink', 'liqueur', 'ouzo', 'raki', 'tsikoudia', 'vodka', 'gin', 'rum',
    'μπύρ', 'μπίρ', 'κρασ', 'λευκό κρασ', 'κόκκινο κρασ', 'ροζέ', 'κοκτέιλ', 'κοκτέηλ',
    'ποτ', 'αναψυκτ', 'καφέ', 'καφές', 'χυμ', 'ρακ', 'τσικουδ', 'ούζο', 'λικέρ',
    'ουίσκ', 'κονιάκ', 'αφρώδ', 'απεριτίφ', 'ρόφημα', 'ροφήματ',
]

# 14 αλλεργιογόνα EU 1169/2011 (code, el, en, emoji)
EU_ALLERGENS = [
    ('gluten',      'Γλουτένη (δημητριακά)',   'Cereals containing gluten', '🌾'),
    ('crustaceans', 'Οστρακοειδή',             'Crustaceans',               '🦐'),
    ('eggs',        'Αυγά',                     'Eggs',                      '🥚'),
    ('fish',        'Ψάρια',                    'Fish',                      '🐟'),
    ('peanuts',     'Αραχίδες (φιστίκια)',      'Peanuts',                   '🥜'),
    ('soybeans',    'Σόγια',                    'Soybeans',                  '🫘'),
    ('milk',        'Γάλα',                     'Milk',                      '🥛'),
    ('nuts',        'Ξηροί καρποί',             'Tree nuts',                 '🌰'),
    ('celery',      'Σέλινο',                   'Celery',                    '🥬'),
    ('mustard',     'Μουστάρδα',                'Mustard',                   '🌭'),
    ('sesame',      'Σουσάμι',                  'Sesame',                    '🫓'),
    ('sulphites',   'Διοξείδιο θείου',          'Sulphur dioxide/sulphites', '🍷'),
    ('lupin',       'Λούπινο',                  'Lupin',                     '🌱'),
    ('molluscs',    'Μαλάκια',                  'Molluscs',                  '🐚'),
]


# ── Μοντέλα (νέοι πίνακες· create_all τους δημιουργεί) ────────────────────────
class Outlet(db.Model):
    __tablename__ = 'piato_outlet'
    id            = db.Column(db.Integer, primary_key=True)
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'), index=True, nullable=False)
    name          = db.Column(db.String(120), nullable=False)      # brand (δεν μεταφράζεται)
    otype         = db.Column(db.String(20), default='restaurant')
    hours         = db.Column(db.String(200), default='')
    qr_token      = db.Column(db.String(36), unique=True, index=True)   # δημόσιο
    preview_token = db.Column(db.String(36), unique=True, index=True)   # μυστικό (preview)
    published     = db.Column(db.Boolean, default=False)
    palette       = db.Column(db.String(20), default='olive')   # χρωματικό θέμα guest μενού
    layout        = db.Column(db.String(12), default='grid')     # τρόπος παρουσίασης (grid/spread)
    hero_image    = db.Column(db.String(500), default='')        # φωτό για κάρτα hub / hero
    tagline       = db.Column(db.String(160), default='')        # υπότιτλος (π.χ. «Mediterranean cuisine»)
    review_url    = db.Column(db.String(500), default='')        # legacy (deprecated· αντικαταστάθηκε από τα 3 παρακάτω)
    google_url    = db.Column(db.String(500), default='')        # Google review link
    tripadvisor_url = db.Column(db.String(500), default='')      # TripAdvisor link
    survey_token  = db.Column(db.String(36), default='')         # token υπάρχοντος Survey (Εστία) → /s/<token>
    sort          = db.Column(db.Integer, default=0)
    views         = db.Column(db.Integer, default=0)             # μετρητής δημόσιων προβολών μενού (hub stats)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    categories    = db.relationship('MenuCategory', backref='outlet',
                                    order_by='MenuCategory.sort', cascade='all, delete-orphan')
    menus         = db.relationship('Menu', backref='outlet',
                                    order_by='Menu.sort', cascade='all, delete-orphan')

class Menu(db.Model):
    """Ονομαστό μενού ανά σημείο (Φαγητό/Κρασιά/Cocktails...) — P-082. Κατηγορίες κουμπώνουν με menu_id."""
    __tablename__ = 'piato_menu'
    id         = db.Column(db.Integer, primary_key=True)
    outlet_id  = db.Column(db.Integer, db.ForeignKey('piato_outlet.id'), index=True, nullable=False)
    name_i18n  = db.Column(db.Text, default='{}')                 # JSON {lang: όνομα μενού}
    icon       = db.Column(db.String(30), default='')
    active     = db.Column(db.Boolean, default=True)
    sort       = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class PiatoHotel(db.Model):
    """Ρυθμίσεις Piato ανά ξενοδοχείο (owner: Piato· FK στο Hotel). Οθόνη-hub υποδοχής."""
    __tablename__ = 'piato_hotel'
    id            = db.Column(db.Integer, primary_key=True)
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'), unique=True, index=True, nullable=False)
    hub_token     = db.Column(db.String(36), unique=True, index=True)   # δημόσιο
    hub_preview_token = db.Column(db.String(36), unique=True, index=True)  # ομάδα
    tagline       = db.Column(db.String(200), default='')
    hero_image    = db.Column(db.String(500), default='')
    created_at    = db.Column(db.DateTime, default=datetime.now)
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class MenuCategory(db.Model):
    __tablename__ = 'piato_category'
    id         = db.Column(db.Integer, primary_key=True)
    outlet_id  = db.Column(db.Integer, db.ForeignKey('piato_outlet.id'), index=True, nullable=False)
    menu_id    = db.Column(db.Integer, db.ForeignKey('piato_menu.id'), index=True, nullable=True)  # P-082
    menu       = db.relationship('Menu', backref=db.backref('categories', order_by='MenuCategory.sort'))
    name_i18n  = db.Column(db.Text, default='{}')                 # JSON {lang: τίτλος}
    kind       = db.Column(db.String(8), default='food')          # 'food' | 'drink' (top-level ομαδοποίηση)
    hours      = db.Column(db.String(200), default='')           # διαθεσιμότητα κατηγορίας
    active     = db.Column(db.Boolean, default=True)
    sort       = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    items      = db.relationship('MenuItem', backref='category',
                                 order_by='MenuItem.sort', cascade='all, delete-orphan')

class MenuItem(db.Model):
    __tablename__ = 'piato_item'
    id          = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('piato_category.id'), index=True, nullable=False)
    title_i18n  = db.Column(db.Text, default='{}')
    desc_i18n   = db.Column(db.Text, default='{}')
    price       = db.Column(db.Float, default=0.0)
    photo_url   = db.Column(db.String(500), default='')          # Φ1: URL μόνο
    available   = db.Column(db.Boolean, default=True)            # 86'd toggle
    cost        = db.Column(db.Float, nullable=True)             # menu-engineering (μελλοντικό)
    sort        = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.now)
    updated_at  = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    variants    = db.relationship('ItemVariant', backref='item',
                                  order_by='ItemVariant.sort', cascade='all, delete-orphan')
    modifiers   = db.relationship('ItemModifier', backref='item',
                                  order_by='ItemModifier.sort', cascade='all, delete-orphan')
    allergens   = db.relationship('ItemAllergen', backref='item', cascade='all, delete-orphan')

class ItemVariant(db.Model):
    __tablename__ = 'piato_variant'
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey('piato_item.id'), index=True, nullable=False)
    label_i18n  = db.Column(db.Text, default='{}')
    price_delta = db.Column(db.Float, default=0.0)
    sort        = db.Column(db.Integer, default=0)

class ItemModifier(db.Model):
    __tablename__ = 'piato_modifier'
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey('piato_item.id'), index=True, nullable=False)
    label_i18n  = db.Column(db.Text, default='{}')
    price_delta = db.Column(db.Float, default=0.0)
    sort        = db.Column(db.Integer, default=0)

class Allergen(db.Model):
    __tablename__ = 'piato_allergen'
    id        = db.Column(db.Integer, primary_key=True)
    code      = db.Column(db.String(24), unique=True, index=True)
    name_i18n = db.Column(db.Text, default='{}')
    icon      = db.Column(db.String(8), default='')
    sort      = db.Column(db.Integer, default=0)

class ItemAllergen(db.Model):
    __tablename__ = 'piato_item_allergen'
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey('piato_item.id'), index=True, nullable=False)
    allergen_id = db.Column(db.Integer, db.ForeignKey('piato_allergen.id'), index=True, nullable=False)
    __table_args__ = (db.UniqueConstraint('item_id', 'allergen_id', name='uq_piato_item_allergen'),)


# ── Migration (non-destructive) + seed ───────────────────────────────────────
def ensure_piato_columns():
    """Idempotent· καλείται από app.py ΜΕΤΑ το init_db(). Νέες στήλες = _add_col
    (forward-compat) + seed 14 αλλεργιογόνων. Οι πίνακες φτιάχνονται από create_all."""
    with app.app_context():
        try:
            from app import _add_col
            _add_col('piato_item', 'cost', 'cost FLOAT')
            _add_col('piato_outlet', 'palette', "palette VARCHAR(20) DEFAULT 'olive'")
            _add_col('piato_outlet', 'layout', "layout VARCHAR(12) DEFAULT 'grid'")
            _add_col('piato_outlet', 'hero_image', 'hero_image VARCHAR(500)')
            _add_col('piato_outlet', 'tagline', 'tagline VARCHAR(160)')
            _add_col('piato_outlet', 'review_url', 'review_url VARCHAR(500)')
            _add_col('piato_outlet', 'google_url', 'google_url VARCHAR(500)')
            _add_col('piato_outlet', 'tripadvisor_url', 'tripadvisor_url VARCHAR(500)')
            _add_col('piato_outlet', 'survey_token', 'survey_token VARCHAR(36)')
            _add_col('piato_category', 'kind', "kind VARCHAR(8) DEFAULT 'food'")
            _add_col('piato_outlet', 'views', 'views INTEGER DEFAULT 0')
            _add_col('piato_category', 'menu_id', 'menu_id INTEGER')
        except Exception as e:
            db.session.rollback(); print('[piato] ensure cols skipped:', e)
        seed_allergens()
        seed_category_kinds()
        seed_default_menus()


def seed_default_menus():
    """Idempotent migration (P-082): κατηγορίες με menu_id=NULL μπαίνουν σε default μενού ανά outlet,
    βάσει kind (food→«Φαγητό», drink→«Ποτά»). ΔΕΝ πειράζει κατηγορίες που έχουν ήδη menu_id
    (ώστε ο admin να μην ξεπερνιέται). Τρέχει μόνο πάνω σε ό,τι είναι ακόμη ανάθετο."""
    try:
        unassigned = MenuCategory.query.filter(MenuCategory.menu_id.is_(None)).all()
        if not unassigned:
            return
        defs = {'food': ('Φαγητό', 'ti-tools-kitchen-2', 0), 'drink': ('Ποτά', 'ti-glass-cocktail', 1)}
        by_outlet = {}
        for c in unassigned:
            by_outlet.setdefault(c.outlet_id, []).append(c)
        made = 0
        for oid, cats in by_outlet.items():
            existing = {(_ml(m.name_i18n).get('el') or ''): m for m in Menu.query.filter_by(outlet_id=oid).all()}
            for c in cats:
                kind = c.kind if c.kind in defs else 'food'
                label, icon, srt = defs[kind]
                m = existing.get(label)
                if not m:
                    m = Menu(outlet_id=oid, name_i18n=json.dumps({'el': label}, ensure_ascii=False),
                             icon=icon, sort=srt, active=True)
                    db.session.add(m); db.session.flush()
                    existing[label] = m; made += 1
                c.menu_id = m.id
        db.session.commit()
        if made:
            print('[piato] seeded %d default menus (P-082)' % made)
    except Exception as e:
        db.session.rollback(); print('[piato] seed menus skipped:', e)

def seed_allergens():
    """Seed 14 EU αλλεργιογόνων (μία φορά· idempotent ανά code)."""
    try:
        existing = {a.code for a in Allergen.query.all()}
        n = 0
        for i, (code, el, en, icon) in enumerate(EU_ALLERGENS):
            if code in existing:
                continue
            db.session.add(Allergen(code=code, icon=icon, sort=i,
                                    name_i18n=json.dumps({'el': el, 'en': en}, ensure_ascii=False)))
            n += 1
        if n:
            db.session.commit(); print('[piato] seeded %d allergens' % n)
    except Exception as e:
        db.session.rollback(); print('[piato] seed allergens skipped:', e)


def _looks_like_drink(name_i18n):
    """Heuristic: το όνομα κατηγορίας μοιάζει με «ποτό» (en/el substrings)."""
    d = _ml(name_i18n)
    blob = ' '.join(str(v) for v in d.values()).lower()
    return any(h in blob for h in DRINK_NAME_HINTS)


def seed_category_kinds():
    """Idempotent seed: κατηγορίες με όνομα-ποτού → kind='drink'. Τρέχει ΜΟΝΟ σε
    εγγραφές που έχουν ακόμη το default 'food' (ώστε ο admin να μην ξεπερνιέται)
    και μόνο μία φορά ανά κατηγορία (σφραγίδα _kinds_seeded στο PiatoHotel; εδώ
    απλά: αν ήδη έχει γίνει αλλαγή σε 'drink' κάπου, θεωρούμε ότι το seed έτρεξε)."""
    try:
        cats = MenuCategory.query.all()
        if not cats:
            return
        # Αν υπάρχει ήδη ≥1 κατηγορία 'drink', ο admin/seed έχει ήδη ενεργήσει → μην ξανα-seed.
        if any((c.kind or 'food') == 'drink' for c in cats):
            return
        n = 0
        for c in cats:
            if (c.kind or 'food') == 'food' and _looks_like_drink(c.name_i18n):
                c.kind = 'drink'; n += 1
        if n:
            db.session.commit(); print('[piato] seeded %d drink-category kinds' % n)
    except Exception as e:
        db.session.rollback(); print('[piato] seed kinds skipped:', e)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _tok():
    return uuid.uuid4().hex

def _f(v, d=0.0):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return d

def _i(v, d=0):
    try:
        return int(v)
    except Exception:
        return d

def _ml(js):
    """JSON string -> dict (ασφαλές)."""
    try:
        d = json.loads(js or '{}')
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _ml_get(js, lang):
    """Τιμή για γλώσσα με fallback: lang -> el -> οποιαδήποτε -> ''."""
    d = _ml(js)
    if d.get(lang):
        return d[lang]
    if d.get(DEF_LANG):
        return d[DEF_LANG]
    for v in d.values():
        if v:
            return v
    return ''

def _ml_from_form(prefix):
    """Μάζεψε {lang: τιμή} από πεδία form prefix_<lang> -> JSON string."""
    out = {}
    for c in LANG_CODES:
        v = (request.form.get('%s_%s' % (prefix, c)) or '').strip()
        if v:
            out[c] = v
    return json.dumps(out, ensure_ascii=False)

def _can_manage():
    return has_rank(ROLE_RANK['manager'])

def _my_hids():
    """Σύνολο hotel_id που ο χρήστης μπορεί να διαχειριστεί (admin=όλα, αλλιώς assigned)."""
    return {h.id for h in allowed_hotels(current_user())}

def _outlet_or_403(oid):
    """Φέρε outlet + έλεγξε hotel scope· αλλιώς 403/404."""
    o = Outlet.query.get(_i(oid))
    if not o:
        abort(404)
    if o.hotel_id not in _my_hids():
        abort(403)
    return o

def _cur_lang():
    l = (request.args.get('lang') or DEF_LANG).lower()
    return l if l in LANG_CODES else DEF_LANG


# ── Guest-facing menu builder (κοινό για public + preview) ────────────────────
def _build_menu(outlet, lang):
    """Δομή για το guest template: κατηγορίες -> πιάτα (localized) + αλλεργιογόνα."""
    allg = {a.id: a for a in Allergen.query.all()}
    cats = []
    for c in outlet.categories:
        if not c.active:
            continue
        items = []
        for it in c.items:
            acodes = [allg[ia.allergen_id].code for ia in it.allergens if ia.allergen_id in allg]
            aicons = [{'code': allg[ia.allergen_id].code,
                       'icon': allg[ia.allergen_id].icon,
                       'name': _ml_get(allg[ia.allergen_id].name_i18n, lang)}
                      for ia in it.allergens if ia.allergen_id in allg]
            items.append({
                'id': it.id,
                'title': _ml_get(it.title_i18n, lang),
                'desc': _ml_get(it.desc_i18n, lang),
                'price': it.price or 0.0,
                'photo': it.photo_url or '',
                'available': bool(it.available),
                'allergen_codes': acodes,
                'allergens': aicons,
                'variants': [{'label': _ml_get(v.label_i18n, lang), 'delta': v.price_delta or 0.0}
                             for v in it.variants],
                'modifiers': [{'label': _ml_get(m.label_i18n, lang), 'delta': m.price_delta or 0.0}
                              for m in it.modifiers],
            })
        if items:
            cats.append({'id': c.id, 'name': _ml_get(c.name_i18n, lang),
                         'kind': (c.kind if c.kind in KIND_CODES else 'food'),
                         'menu_id': c.menu_id,
                         'hours': c.hours or '', 'dishes': items})
    allergen_master = [{'code': a.code, 'icon': a.icon, 'name': _ml_get(a.name_i18n, lang)}
                       for a in sorted(allg.values(), key=lambda x: x.sort)]
    return cats, allergen_master


def _render_menu(outlet, preview=False):
    lang = _cur_lang()
    cats, allergens = _build_menu(outlet, lang)
    h = Hotel.query.get(outlet.hotel_id)
    # Back-link προς το hub του ξενοδοχείου (get-or-create ώστε να υπάρχει πάντα token).
    hub = _hub_for(outlet.hotel_id)
    hub_link = ('/piato/h/preview/' + hub.hub_preview_token) if preview else ('/piato/h/' + hub.hub_token)
    # Ομαδοποίηση ανά ΜΕΝΟΥ (P-082· Φαγητό/Ποτά/Cocktails...) — μόνο μενού με ≥1 κατηγορία.
    # Fallback: αν το σημείο δεν έχει μενού (παλιά δεδομένα πριν το migration), ομαδοποίηση food/drink.
    menus = sorted(outlet.menus, key=lambda m: (m.sort or 0, m.id))
    groups = []
    if menus:
        known = {m.id for m in menus}
        for m in menus:
            gcats = [c for c in cats if c.get('menu_id') == m.id]
            if gcats:
                groups.append({'code': 'menu%d' % m.id, 'label': _ml_get(m.name_i18n, lang) or 'Menu',
                               'icon': m.icon or '', 'cats': gcats})
        orphan = [c for c in cats if c.get('menu_id') not in known]
        if orphan:
            groups.append({'code': 'other', 'label': _ui(lang).get('more_menu', 'Μενού'), 'icon': '', 'cats': orphan})
    else:
        for code, label in PIATO_KINDS:
            gcats = [c for c in cats if c.get('kind', 'food') == code]
            if gcats:
                groups.append({'code': code, 'label': label, 'icon': '', 'cats': gcats})
    return render_template('piato_menu.html',
                           outlet=outlet, hotel_name=(h.name if h else ''),
                           cats=cats, groups=groups, allergens=allergens,
                           langs=PIATO_LANGS, lang=lang, preview=preview,
                           hub_link=hub_link, T=_ui(lang))


# ── GUEST ROUTES (public — χωρίς login) ──────────────────────────────────────
@app.route('/piato/<qr_token>')
def piato_public(qr_token):
    o = Outlet.query.filter_by(qr_token=qr_token).first()
    if not o or not o.published:
        abort(404)                       # draft/άγνωστο -> μη διαθέσιμο για το κοινό
    try:                                 # μετρητής προβολών (hub stats)· μη-κρίσιμο
        o.views = (o.views or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
    return _render_menu(o, preview=False)

@app.route('/piato/preview/<preview_token>')
def piato_preview(preview_token):
    o = Outlet.query.filter_by(preview_token=preview_token).first()
    if not o:
        abort(404)
    return _render_menu(o, preview=True)  # ορατό ανεξαρτήτως published (μυστικό token)


# ── HUB (οθόνη υποδοχής ξενοδοχείου → επιλογή outlet) ────────────────────────
def _hub_for(hotel_id):
    """get-or-create ρυθμίσεων hub για ξενοδοχείο (owner-screen: admin console)."""
    hub = PiatoHotel.query.filter_by(hotel_id=hotel_id).first()
    if not hub:
        hub = PiatoHotel(hotel_id=hotel_id, hub_token=_tok(), hub_preview_token=_tok())
        db.session.add(hub); db.session.commit()
    return hub

def _hub_cards(hotel_id, preview):
    q = Outlet.query.filter_by(hotel_id=hotel_id)
    if not preview:
        q = q.filter_by(published=True)
    cards = []
    for o in q.order_by(Outlet.sort, Outlet.name).all():
        link = ('/piato/preview/' + o.preview_token) if preview else ('/piato/' + o.qr_token)
        # Τι σερβίρει το σημείο (φαγητό/ποτό) — από τις ενεργές κατηγορίες με πιάτα → εικονίδια hub.
        kinds = {(c.kind if c.kind in KIND_CODES else 'food')
                 for c in o.categories if c.active and c.items}
        cards.append({'name': o.name, 'otype': o.otype, 'otype_label': OTYPE_LABEL.get(o.otype, o.otype),
                      'has_food': 'food' in kinds, 'has_drink': 'drink' in kinds,
                      'tagline': o.tagline or '', 'hero': o.hero_image or '',
                      'palette': o.palette or 'olive', 'hours': o.hours or '',
                      'link': link, 'published': bool(o.published)})
    return cards

def _render_hub(hub, preview=False):
    h = Hotel.query.get(hub.hotel_id)
    return render_template('piato_hub.html', hub=hub, hotel_name=(h.name if h else ''),
                           cards=_hub_cards(hub.hotel_id, preview),
                           langs=PIATO_LANGS, lang=_cur_lang(), preview=preview)

@app.route('/piato/h/<hub_token>')
def piato_hub_public(hub_token):
    hub = PiatoHotel.query.filter_by(hub_token=hub_token).first()
    if not hub:
        abort(404)
    return _render_hub(hub, preview=False)

@app.route('/piato/h/preview/<token>')
def piato_hub_preview(token):
    hub = PiatoHotel.query.filter_by(hub_preview_token=token).first()
    if not hub:
        abort(404)
    return _render_hub(hub, preview=True)


# ── ADMIN CONSOLE ────────────────────────────────────────────────────────────
@app.route('/dashboard/piato')
def piato_admin():
    if not _can_manage():
        return redirect(url_for('login'))
    my = _my_hids()
    aid = active_hotel_id()
    q = Outlet.query.filter(Outlet.hotel_id.in_(my or {-1}))
    if aid and aid in my:
        q = q.filter(Outlet.hotel_id == aid)
    outlets = q.order_by(Outlet.hotel_id, Outlet.sort, Outlet.name).all()
    hn = {h.id: h.name for h in Hotel.query.all()}
    sel = None
    oid = request.args.get('outlet', type=int)
    if oid:
        sel = Outlet.query.get(oid)
        if sel and sel.hotel_id not in my:
            sel = None
    hotels = [h for h in allowed_hotels(current_user())]
    allergens = sorted(Allergen.query.all(), key=lambda a: a.sort)
    # hub links: get-or-create ρυθμίσεις ανά ξενοδοχείο που έχει ≥1 outlet
    hotels_with_outlets = {o.hotel_id for o in outlets}
    hubs = {hid: _hub_for(hid) for hid in hotels_with_outlets}
    # Ερωτηματολόγια (Surveys module) στο scope — για το dropdown «Ερωτηματολόγιο» ανά outlet.
    surveys = []
    try:
        from surveys import Survey
        surveys = (Survey.query
                   .filter(db.or_(Survey.hotel_id.in_(my or {-1}), Survey.hotel_id.is_(None)))
                   .order_by(Survey.title).all())
    except Exception as e:
        print('[piato] surveys list skipped:', e)
    stats = _outlet_stats(sel) if sel else None
    menus = sorted(sel.menus, key=lambda m: (m.sort or 0, m.id)) if sel else []
    orphan_cats = [c for c in sel.categories if not c.menu_id] if sel else []
    if sel and orphan_cats:                       # self-heal: ανάθετες κατηγορίες → default μενού
        seed_default_menus()
        db.session.expire_all()
        sel = Outlet.query.get(sel.id)
        menus = sorted(sel.menus, key=lambda m: (m.sort or 0, m.id))
        orphan_cats = [c for c in sel.categories if not c.menu_id]
    return render_template('piato_admin.html',
                           outlets=outlets, hotel_names=hn, sel=sel, hotels=hotels,
                           langs=PIATO_LANGS, otypes=OUTLET_TYPES, otype_label=OTYPE_LABEL,
                           allergens=allergens, ml=_ml, mlget=_ml_get, hubs=hubs,
                           palettes=PIATO_PALETTES, layouts=PIATO_LAYOUTS, kinds=PIATO_KINDS,
                           surveys=surveys, stats=stats, menus=menus, orphan_cats=orphan_cats,
                           base_url=request.host_url.rstrip('/'))


def _outlet_stats(o):
    """Στατιστικά επισκόπησης ενός outlet για το hub (από υπάρχοντα δεδομένα)."""
    cats = list(o.categories)
    items = [it for c in cats for it in c.items]
    lang_codes = [code for code, _ in PIATO_LANGS]
    slots = filled = 0
    for it in items:
        ti = _ml(it.title_i18n)
        for lc in lang_codes:
            slots += 1
            if (ti.get(lc) or '').strip():
                filled += 1
    return {
        'cats': len(cats),
        'items': len(items),
        'unavail': sum(1 for it in items if not it.available),
        'tpct': round(100 * filled / slots) if slots else 0,
        'views': o.views or 0,
        'published': bool(o.published),
        'updated': o.updated_at,
        'active_cats': sum(1 for c in cats if c.active),
    }


# ── PRINTED PDF MENU (Βήμα 3· branded, fpdf2 + DejaVu — reuse pool-report pattern) ──
def build_menu_pdf(outlet, lang='el'):
    from fpdf import FPDF
    from app import BASE_DIR
    import os as _os
    NAVY = (25, 56, 71); GOLD = (187, 149, 73); GREY = (120, 120, 120); DARK = (40, 40, 40)
    fdir = _os.path.join(BASE_DIR, 'assets', 'fonts')
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_font('dv', '', _os.path.join(fdir, 'DejaVuSans.ttf'))
    pdf.add_font('dv', 'B', _os.path.join(fdir, 'DejaVuSans-Bold.ttf'))
    pdf.add_page()
    try:
        pdf.image(_os.path.join(BASE_DIR, 'static', 'img', 'logo.png'), x=12, y=11, h=13)
    except Exception:
        pass
    hotel = Hotel.query.get(outlet.hotel_id)
    pdf.set_xy(30, 11); pdf.set_font('dv', 'B', 18); pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, outlet.name, ln=1)
    pdf.set_x(30); pdf.set_font('dv', '', 11); pdf.set_text_color(*GREY)
    sub = (hotel.name if hotel else '') + ((' · ' + outlet.tagline) if outlet.tagline else '')
    pdf.cell(0, 6, sub, ln=1)
    pdf.ln(5)
    pdf.set_draw_color(*GOLD); pdf.set_line_width(0.6); y = pdf.get_y(); pdf.line(12, y, 198, y); pdf.ln(4)

    def price_str(p):
        try:
            return ('%.2f' % float(p)).replace('.', ',') + ' €'
        except Exception:
            return ''

    def pick(i18n):
        d = _ml(i18n)
        return (d.get(lang) or d.get('el') or '').strip()

    any_item = False
    for c in outlet.categories:
        if not c.active:
            continue
        its = [it for it in c.items if it.available]
        if not its:
            continue
        any_item = True
        pdf.ln(2); pdf.set_font('dv', 'B', 13); pdf.set_text_color(*NAVY); pdf.set_fill_color(242, 245, 247)
        pdf.cell(0, 8, '  ' + pick(c.name_i18n), ln=1, fill=True); pdf.ln(1)
        for it in its:
            title = pick(it.title_i18n); desc = pick(it.desc_i18n)
            pr = price_str(it.price) if it.price else ''
            pdf.set_font('dv', 'B', 11); pdf.set_text_color(*DARK); pdf.cell(150, 6, title)
            pdf.set_font('dv', '', 11); pdf.set_text_color(*NAVY); pdf.cell(0, 6, pr, ln=1, align='R')
            if desc:
                pdf.set_font('dv', '', 9.5); pdf.set_text_color(*GREY); pdf.multi_cell(0, 4.6, desc)
            pdf.ln(1)
    if not any_item:
        pdf.set_font('dv', '', 12); pdf.set_text_color(*GREY)
        pdf.cell(0, 8, 'Δεν υπάρχουν διαθέσιμα πιάτα.', ln=1)
    pdf.ln(5); pdf.set_font('dv', '', 8); pdf.set_text_color(*GREY)
    pdf.cell(0, 5, 'Powered by Piato · Εστία · CONDIAN Hotels', ln=1, align='C')
    return bytes(pdf.output())


@app.route('/dashboard/piato/pdf/<int:outlet_id>')
def piato_menu_pdf(outlet_id):
    if not _can_manage():
        return redirect(url_for('login'))
    o = Outlet.query.get(outlet_id)
    if not o or o.hotel_id not in _my_hids():
        abort(404)
    lang = request.args.get('lang', 'el')
    if lang not in LANG_CODES:
        lang = 'el'
    try:
        data = build_menu_pdf(o, lang)
    except Exception as e:
        print('[piato] menu pdf error:', e)
        abort(500)
    log_activity('piato_menu_pdf', '%s (%s)' % (o.name, lang))
    fname = 'piato-menu-%d-%s.pdf' % (o.id, lang)
    return app.response_class(data, mimetype='application/pdf',
                              headers={'Content-Disposition': 'inline; filename=' + fname})


# ── OUTLET CRUD ──────────────────────────────────────────────────────────────
@app.route('/dashboard/piato/outlet/save', methods=['POST'])
def piato_outlet_save():
    if not _can_manage():
        return redirect(url_for('login'))
    oid = request.form.get('id')
    name = (request.form.get('name') or '').strip()
    hid = _i(request.form.get('hotel_id'))
    otype = request.form.get('otype') or 'restaurant'
    hours = (request.form.get('hours') or '').strip()
    palette = request.form.get('palette') or 'olive'
    if palette not in PALETTE_CODES:
        palette = 'olive'
    layout = request.form.get('layout') or 'grid'
    if layout not in LAYOUT_CODES:
        layout = 'grid'
    hero = (request.form.get('hero_image') or '').strip()
    tagline = (request.form.get('tagline') or '').strip()
    google_url = (request.form.get('google_url') or '').strip()
    tripadvisor_url = (request.form.get('tripadvisor_url') or '').strip()
    survey_token = (request.form.get('survey_token') or '').strip()
    if not name or hid not in _my_hids():
        return redirect(url_for('piato_admin'))
    if oid:
        o = _outlet_or_403(oid)
        o.name, o.otype, o.hours = name, otype, hours
        o.palette, o.layout, o.hero_image, o.tagline = palette, layout, hero, tagline
        o.google_url, o.tripadvisor_url, o.survey_token = google_url, tripadvisor_url, survey_token
        # hotel_id αλλάζει μόνο αν το νέο είναι στο scope
        if hid in _my_hids():
            o.hotel_id = hid
        log_activity('piato_outlet_edit', name)
    else:
        o = Outlet(hotel_id=hid, name=name, otype=otype, hours=hours,
                   palette=palette, layout=layout, hero_image=hero, tagline=tagline,
                   google_url=google_url, tripadvisor_url=tripadvisor_url, survey_token=survey_token,
                   qr_token=_tok(), preview_token=_tok(), published=False)
        db.session.add(o)
        log_activity('piato_outlet_add', name)
    db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id))

@app.route('/dashboard/piato/outlet/publish', methods=['POST'])
def piato_outlet_publish():
    if not _can_manage():
        return redirect(url_for('login'))
    o = _outlet_or_403(request.form.get('id'))
    o.published = (request.form.get('to') == '1')
    db.session.commit()
    log_activity('piato_outlet_publish' if o.published else 'piato_outlet_unpublish', o.name)
    return redirect(url_for('piato_admin', outlet=o.id))

@app.route('/dashboard/piato/outlet/delete', methods=['POST'])
def piato_outlet_delete():
    if not _can_manage():
        return redirect(url_for('login'))
    o = _outlet_or_403(request.form.get('id'))
    nm = o.name
    db.session.delete(o); db.session.commit()
    log_activity('piato_outlet_delete', nm)
    return redirect(url_for('piato_admin'))


# ── CATEGORY CRUD ────────────────────────────────────────────────────────────
@app.route('/dashboard/piato/category/save', methods=['POST'])
def piato_category_save():
    if not _can_manage():
        return redirect(url_for('login'))
    cid = request.form.get('id')
    o = _outlet_or_403(request.form.get('outlet_id'))
    name = _ml_from_form('cname')
    hours = (request.form.get('chours') or '').strip()
    kind = request.form.get('kind') or 'food'
    if kind not in KIND_CODES:
        kind = 'food'
    menu_id = _i(request.form.get('menu_id')) or None       # P-082: μενού-στόχος
    if menu_id:
        m = Menu.query.get(menu_id)
        if not m or m.outlet_id != o.id:
            menu_id = None
    if cid:
        c = MenuCategory.query.get(_i(cid))
        if not c or c.outlet_id != o.id:
            abort(404)
        c.name_i18n, c.hours, c.kind = name, hours, kind
        if menu_id:
            c.menu_id = menu_id
    else:
        mx = db.session.query(db.func.max(MenuCategory.sort)).filter_by(outlet_id=o.id).scalar() or 0
        c = MenuCategory(outlet_id=o.id, name_i18n=name, hours=hours, kind=kind, sort=mx + 1, menu_id=menu_id)
        db.session.add(c)
    db.session.commit()
    log_activity('piato_category_save', o.name)
    return redirect(url_for('piato_admin', outlet=o.id))

@app.route('/dashboard/piato/category/delete', methods=['POST'])
def piato_category_delete():
    if not _can_manage():
        return redirect(url_for('login'))
    c = MenuCategory.query.get(_i(request.form.get('id')))
    if not c:
        abort(404)
    o = _outlet_or_403(c.outlet_id)
    db.session.delete(c); db.session.commit()
    log_activity('piato_category_delete', o.name)
    return redirect(url_for('piato_admin', outlet=o.id))


def _reorder(rows, row_id, direction):
    """Μετακίνησε τη γραμμή row_id up/down μέσα στη λίστα rows· ξαναγράφει sort=θέση (contiguous).
    Επιστρέφει True αν άλλαξε κάτι (χρειάζεται commit)."""
    lst = sorted(rows, key=lambda x: (x.sort or 0, x.id))
    idx = next((k for k, x in enumerate(lst) if x.id == row_id), None)
    if idx is None:
        return False
    j = idx - 1 if direction == 'up' else idx + 1
    if j < 0 or j >= len(lst):
        return False
    lst[idx], lst[j] = lst[j], lst[idx]
    for k, x in enumerate(lst):
        x.sort = k
    return True


@app.route('/dashboard/piato/category/move', methods=['POST'])
def piato_category_move():
    if not _can_manage():
        return redirect(url_for('login'))
    c = MenuCategory.query.get(_i(request.form.get('id')))
    if not c:
        abort(404)
    o = _outlet_or_403(c.outlet_id)
    if _reorder(list(o.categories), c.id, request.form.get('dir')):
        db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)


@app.route('/dashboard/piato/category/reorder', methods=['POST'])
def piato_category_reorder():
    """Drag&drop αναδιάταξη κατηγοριών (Βήμα 5α): ids = νέα σειρά → sort=index."""
    if not _can_manage():
        return jsonify(error='forbidden'), 403
    o = _outlet_or_403(_i(request.form.get('outlet_id')))
    menu_id = _i(request.form.get('menu_id')) or None       # P-082: μενού-στόχος (drag μεταξύ μενού)
    if menu_id:
        m = Menu.query.get(menu_id)
        if not m or m.outlet_id != o.id:
            menu_id = None
    valid = {c.id for c in o.categories}
    ids = [int(x) for x in request.form.get('ids', '').split(',') if x.strip().isdigit()]
    for i, cid in enumerate(ids):
        if cid in valid:
            c = MenuCategory.query.get(cid)
            if c:
                c.sort = i
                if menu_id:
                    c.menu_id = menu_id
    db.session.commit()
    return jsonify(ok=True)


@app.route('/dashboard/piato/item/reorder', methods=['POST'])
def piato_item_reorder():
    """Drag&drop αναδιάταξη/μετακίνηση πιάτων (Βήμα 5α): ids = νέα σειρά της κατηγορίας-στόχου·
    κάθε πιάτο παίρνει category_id=στόχος + sort=index (χειρίζεται και μετακίνηση σε άλλη κατηγορία)."""
    if not _can_manage():
        return jsonify(error='forbidden'), 403
    cat = MenuCategory.query.get(_i(request.form.get('category_id')))
    if not cat:
        return jsonify(error='not_found'), 404
    _outlet_or_403(cat.outlet_id)                 # scope: η κατηγορία-στόχος στα δικά μου ξενοδοχεία
    my = _my_hids()
    ids = [int(x) for x in request.form.get('ids', '').split(',') if x.strip().isdigit()]
    for i, iid in enumerate(ids):
        it = MenuItem.query.get(iid)
        if it and it.category and it.category.outlet and it.category.outlet.hotel_id in my:
            it.category_id = cat.id
            it.sort = i
    db.session.commit()
    return jsonify(ok=True)


# ── MENU CRUD (P-082 · ονομαστά μενού ανά σημείο) ────────────────────────────
@app.route('/dashboard/piato/menu/save', methods=['POST'])
def piato_menu_save():
    if not _can_manage():
        return redirect(url_for('login'))
    o = _outlet_or_403(request.form.get('outlet_id'))
    mid = request.form.get('id')
    name = _ml_from_form('mname')
    icon = (request.form.get('icon') or '').strip()[:30]
    if mid:
        m = Menu.query.get(_i(mid))
        if not m or m.outlet_id != o.id:
            abort(404)
        m.name_i18n = name
        if icon:
            m.icon = icon
    else:
        mx = db.session.query(db.func.max(Menu.sort)).filter_by(outlet_id=o.id).scalar() or 0
        db.session.add(Menu(outlet_id=o.id, name_i18n=name, icon=icon, sort=mx + 1, active=True))
    db.session.commit()
    log_activity('piato_menu_save', o.name)
    return redirect(url_for('piato_admin', outlet=o.id))


@app.route('/dashboard/piato/menu/delete', methods=['POST'])
def piato_menu_delete():
    if not _can_manage():
        return redirect(url_for('login'))
    m = Menu.query.get(_i(request.form.get('id')))
    if not m:
        abort(404)
    o = _outlet_or_403(m.outlet_id)
    cats = list(m.categories)
    if cats:
        other = Menu.query.filter(Menu.outlet_id == o.id, Menu.id != m.id).order_by(Menu.sort).first()
        if not other:
            return redirect(url_for('piato_admin', outlet=o.id))   # δεν σβήνεις το μοναδικό μενού που κρατά κατηγορίες
        for c in cats:
            c.menu_id = other.id
    db.session.delete(m); db.session.commit()
    log_activity('piato_menu_delete', o.name)
    return redirect(url_for('piato_admin', outlet=o.id))


@app.route('/dashboard/piato/menu/reorder', methods=['POST'])
def piato_menu_reorder():
    if not _can_manage():
        return jsonify(error='forbidden'), 403
    o = _outlet_or_403(_i(request.form.get('outlet_id')))
    valid = {m.id for m in o.menus}
    ids = [int(x) for x in request.form.get('ids', '').split(',') if x.strip().isdigit()]
    for i, mid in enumerate(ids):
        if mid in valid:
            m = Menu.query.get(mid)
            if m:
                m.sort = i
    db.session.commit()
    return jsonify(ok=True)


# ── ITEM CRUD ────────────────────────────────────────────────────────────────
@app.route('/dashboard/piato/item/save', methods=['POST'])
def piato_item_save():
    if not _can_manage():
        return redirect(url_for('login'))
    iid = request.form.get('id')
    c = MenuCategory.query.get(_i(request.form.get('category_id')))
    if not c:
        abort(404)
    o = _outlet_or_403(c.outlet_id)
    title = _ml_from_form('title')
    desc = _ml_from_form('desc')
    price = _f(request.form.get('price'))
    photo = (request.form.get('photo_url') or '').strip()
    cost = request.form.get('cost')
    cost = _f(cost) if (cost or '').strip() else None
    avail = request.form.get('available') == '1'
    sel_allg = set(request.form.getlist('allergens'))   # allergen ids (str)
    if iid:
        it = MenuItem.query.get(_i(iid))
        if not it or it.category_id != c.id:
            abort(404)
        it.title_i18n, it.desc_i18n = title, desc
        it.price, it.photo_url, it.cost, it.available = price, photo, cost, avail
    else:
        mx = db.session.query(db.func.max(MenuItem.sort)).filter_by(category_id=c.id).scalar() or 0
        it = MenuItem(category_id=c.id, title_i18n=title, desc_i18n=desc, price=price,
                      photo_url=photo, cost=cost, available=avail, sort=mx + 1)
        db.session.add(it); db.session.flush()
    # allergens (αντικατάσταση set)
    ItemAllergen.query.filter_by(item_id=it.id).delete()
    for aid in sel_allg:
        if aid.isdigit():
            db.session.add(ItemAllergen(item_id=it.id, allergen_id=int(aid)))
    db.session.commit()
    log_activity('piato_item_save', _ml_get(title, DEF_LANG))
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)

@app.route('/dashboard/piato/item/available', methods=['POST'])
def piato_item_available():
    """86'd γρήγορο toggle."""
    if not _can_manage():
        return redirect(url_for('login'))
    it = MenuItem.query.get(_i(request.form.get('id')))
    if not it:
        abort(404)
    o = _outlet_or_403(MenuCategory.query.get(it.category_id).outlet_id)
    it.available = (request.form.get('to') == '1')
    db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % it.category_id)

@app.route('/dashboard/piato/item/delete', methods=['POST'])
def piato_item_delete():
    if not _can_manage():
        return redirect(url_for('login'))
    it = MenuItem.query.get(_i(request.form.get('id')))
    if not it:
        abort(404)
    c = MenuCategory.query.get(it.category_id)
    o = _outlet_or_403(c.outlet_id)
    db.session.delete(it); db.session.commit()
    log_activity('piato_item_delete', o.name)
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)


@app.route('/dashboard/piato/item/move', methods=['POST'])
def piato_item_move():
    if not _can_manage():
        return redirect(url_for('login'))
    it = MenuItem.query.get(_i(request.form.get('id')))
    if not it:
        abort(404)
    c = MenuCategory.query.get(it.category_id)
    o = _outlet_or_403(c.outlet_id)
    if _reorder(list(c.items), it.id, request.form.get('dir')):
        db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)


# ── VARIANT / MODIFIER (κοινά endpoints· kind=variant|modifier) ──────────────
def _vm_model(kind):
    return ItemModifier if kind == 'modifier' else ItemVariant

@app.route('/dashboard/piato/vm/save', methods=['POST'])
def piato_vm_save():
    if not _can_manage():
        return redirect(url_for('login'))
    kind = request.form.get('kind') or 'variant'
    it = MenuItem.query.get(_i(request.form.get('item_id')))
    if not it:
        abort(404)
    c = MenuCategory.query.get(it.category_id)
    o = _outlet_or_403(c.outlet_id)
    Model = _vm_model(kind)
    label = _ml_from_form('vmlabel')
    delta = _f(request.form.get('delta'))
    mx = db.session.query(db.func.max(Model.sort)).filter_by(item_id=it.id).scalar() or 0
    db.session.add(Model(item_id=it.id, label_i18n=label, price_delta=delta, sort=mx + 1))
    db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)

@app.route('/dashboard/piato/vm/delete', methods=['POST'])
def piato_vm_delete():
    if not _can_manage():
        return redirect(url_for('login'))
    kind = request.form.get('kind') or 'variant'
    Model = _vm_model(kind)
    row = Model.query.get(_i(request.form.get('id')))
    if not row:
        abort(404)
    it = MenuItem.query.get(row.item_id)
    c = MenuCategory.query.get(it.category_id)
    o = _outlet_or_403(c.outlet_id)
    db.session.delete(row); db.session.commit()
    return redirect(url_for('piato_admin', outlet=o.id) + '#cat%d' % c.id)


# ── AI: δημιουργία περιγραφής πιάτου (reuse call_llm· στέλνει ΜΟΝΟ τίτλο+αλλεργιογόνα) ──────────
@app.route('/dashboard/piato/ai/describe', methods=['POST'])
def piato_ai_describe():
    if not _can_manage():
        return jsonify(error='forbidden'), 403
    from app import call_llm, ai_allowed
    if not ai_allowed('piato', 'menu_desc'):
        return jsonify(error='ai_disabled'), 403   # πύλη διακυβέρνησης: κλειστό από την κονσόλα AI
    title = (request.form.get('title') or '').strip()
    if not title:
        return jsonify(error='no_title'), 400
    desc = (request.form.get('desc') or '').strip()       # υπάρχουσα περιγραφή (πηγή· αλλιώς παράγεται)
    allerg = (request.form.get('allergens') or '').strip()
    langs_txt = 'el (Greek), en (English), de (German), it (Italian), fr (French)'
    sys_p = ('You localize restaurant menu items for a Greek hotel. Given a dish name and an optional '
             'description in Greek, produce for EACH language [' + langs_txt + ']: (1) the dish name '
             'translated/localized, and (2) a SHORT appetizing description (12-18 words, no price). '
             'If a Greek description is given, TRANSLATE it faithfully; if not, WRITE a fitting one. '
             'Return ONLY a compact JSON: {"title":{"el":..,"en":..,"de":..,"it":..,"fr":..},'
             '"desc":{"el":..,"en":..,"de":..,"it":..,"fr":..}}. No markdown, no extra text.')
    user_p = 'Dish name (Greek): ' + title
    if desc:
        user_p += '\nDescription (Greek): ' + desc
    if allerg:
        user_p += '\nAllergens: ' + allerg
    reply, err = call_llm(sys_p, [{'role': 'user', 'content': user_p}])
    if err:
        return jsonify(error=err), 502
    import re
    m = re.search(r'\{.*\}', reply or '', re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        data = {}
    t = data.get('title') or {}
    d = data.get('desc') or {}
    out_t = {k: (str(t.get(k) or '')).strip() for k in LANG_CODES}
    out_d = {k: (str(d.get(k) or '')).strip() for k in LANG_CODES}
    if not (any(out_t.values()) or any(out_d.values())):
        return jsonify(error='parse_failed', raw=(reply or '')[:200]), 502
    log_activity('piato_ai_describe', title)
    return jsonify(ok=True, title=out_t, desc=out_d)


print('piato module loaded (F&B μενού — Φ1: μοντέλα + admin CRUD + guest menu + preview/publish + AI describe)')
