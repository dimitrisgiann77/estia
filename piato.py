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
from flask import request, redirect, url_for, render_template, abort
from app import (app, db, current_user, is_admin, allowed_hotels, active_hotel_id,
                 log_activity, has_rank, ROLE_RANK, Hotel)


# ── Σταθερές ──────────────────────────────────────────────────────────────────
# Γλώσσες μενού (guest-facing· πρώτη = προεπιλογή/fallback). Εύκολα επεκτάσιμο.
PIATO_LANGS = [('el', 'Ελληνικά'), ('en', 'English'), ('de', 'Deutsch'),
               ('fr', 'Français'), ('it', 'Italiano'), ('ru', 'Русский'),
               ('bg', 'Български')]
LANG_CODES = [c for c, _ in PIATO_LANGS]
DEF_LANG = 'el'

OUTLET_TYPES = [('restaurant', 'Εστιατόριο'), ('bar', 'Μπαρ'),
                ('pool_bar', 'Pool bar'), ('beach_bar', 'Beach bar'),
                ('room_service', 'Room service'), ('cafe', 'Café')]
OTYPE_LABEL = {k: v for k, v in OUTLET_TYPES}

# Παλέτες guest μενού (code, label). Πρώτη = προεπιλογή. (aegean = Boho Earth φωτεινό)
PIATO_PALETTES = [('olive', 'Olive & Brass'), ('aegean', 'Boho Earth (φωτεινό)'),
                  ('charcoal', 'Charcoal & Gold'), ('ink', 'Ink & Amber')]
PALETTE_CODES = [c for c, _ in PIATO_PALETTES]

# Τρόποι παρουσίασης μενού (code, label). Πρώτη = προεπιλογή.
PIATO_LAYOUTS = [('grid', 'Πλέγμα (κάρτες)'), ('spread', 'Δίστηλο (magazine)')]
LAYOUT_CODES = [c for c, _ in PIATO_LAYOUTS]

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
    sort          = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    categories    = db.relationship('MenuCategory', backref='outlet',
                                    order_by='MenuCategory.sort', cascade='all, delete-orphan')

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
    name_i18n  = db.Column(db.Text, default='{}')                 # JSON {lang: τίτλος}
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
        except Exception as e:
            db.session.rollback(); print('[piato] ensure cols skipped:', e)
        seed_allergens()

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
                         'hours': c.hours or '', 'dishes': items})
    allergen_master = [{'code': a.code, 'icon': a.icon, 'name': _ml_get(a.name_i18n, lang)}
                       for a in sorted(allg.values(), key=lambda x: x.sort)]
    return cats, allergen_master


def _render_menu(outlet, preview=False):
    lang = _cur_lang()
    cats, allergens = _build_menu(outlet, lang)
    h = Hotel.query.get(outlet.hotel_id)
    return render_template('piato_menu.html',
                           outlet=outlet, hotel_name=(h.name if h else ''),
                           cats=cats, allergens=allergens,
                           langs=PIATO_LANGS, lang=lang, preview=preview)


# ── GUEST ROUTES (public — χωρίς login) ──────────────────────────────────────
@app.route('/piato/<qr_token>')
def piato_public(qr_token):
    o = Outlet.query.filter_by(qr_token=qr_token).first()
    if not o or not o.published:
        abort(404)                       # draft/άγνωστο -> μη διαθέσιμο για το κοινό
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
        cards.append({'name': o.name, 'otype': o.otype, 'otype_label': OTYPE_LABEL.get(o.otype, o.otype),
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
    return render_template('piato_admin.html',
                           outlets=outlets, hotel_names=hn, sel=sel, hotels=hotels,
                           langs=PIATO_LANGS, otypes=OUTLET_TYPES, otype_label=OTYPE_LABEL,
                           allergens=allergens, ml=_ml, mlget=_ml_get, hubs=hubs,
                           palettes=PIATO_PALETTES, layouts=PIATO_LAYOUTS,
                           base_url=request.host_url.rstrip('/'))


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
    if not name or hid not in _my_hids():
        return redirect(url_for('piato_admin'))
    if oid:
        o = _outlet_or_403(oid)
        o.name, o.otype, o.hours = name, otype, hours
        o.palette, o.layout, o.hero_image, o.tagline = palette, layout, hero, tagline
        # hotel_id αλλάζει μόνο αν το νέο είναι στο scope
        if hid in _my_hids():
            o.hotel_id = hid
        log_activity('piato_outlet_edit', name)
    else:
        o = Outlet(hotel_id=hid, name=name, otype=otype, hours=hours,
                   palette=palette, layout=layout, hero_image=hero, tagline=tagline,
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
    if cid:
        c = MenuCategory.query.get(_i(cid))
        if not c or c.outlet_id != o.id:
            abort(404)
        c.name_i18n, c.hours = name, hours
    else:
        mx = db.session.query(db.func.max(MenuCategory.sort)).filter_by(outlet_id=o.id).scalar() or 0
        c = MenuCategory(outlet_id=o.id, name_i18n=name, hours=hours, sort=mx + 1)
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


print('piato module loaded (F&B μενού — Φ1: μοντέλα + admin CRUD + guest menu + preview/publish)')
